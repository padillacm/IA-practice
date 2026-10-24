# Spec Delta

## Purpose

Permite al candidato configurar y conducir una sesión de entrevista simulada de Netflix para roles de ML, eligiendo rol, nivel, idioma y qué etapas practicar, y orquesta el paso entre etapas.

## ADDED Requirements

### Requirement: Inicio de sesión con configuración explícita
El sistema SHALL iniciar cada sesión pidiendo o aceptando como argumento: rol (ML Engineer, Research Scientist, Applied/Data Scientist), nivel objetivo (L4, L5, L6), idioma y etapas a simular. No SHALL comenzar ninguna etapa hasta que estos valores estén definidos y confirmados por el candidato.

#### Scenario: Configuración interactiva
- **WHEN** el candidato invoca `/netflix-ml-interview` sin argumentos
- **THEN** el sistema pregunta rol, nivel, idioma y etapas, muestra un resumen de la configuración y espera confirmación antes de empezar

#### Scenario: Configuración por argumentos
- **WHEN** el candidato invoca `/netflix-ml-interview role=mle level=L5 stages=ml-system-design`
- **THEN** el sistema usa el idioma por defecto, muestra el resumen y pide confirmación

#### Scenario: Valor inválido
- **WHEN** el candidato indica una etapa, rol, nivel o idioma que no existe
- **THEN** el sistema rechaza el valor, lista las opciones válidas y no inicia la sesión

### Requirement: Idioma único de la sesión
El idioma por defecto SHALL ser inglés para todo: la configuración, la entrevista, los scorecards, el debrief y el plan de estudio. Con la opción `lang=es`, todo ello SHALL ser en español. Los términos técnicos estándar (p. ej. NDCG, two-tower) se mantienen en inglés en ambos modos.

#### Scenario: Por defecto en inglés
- **WHEN** el candidato no indica idioma
- **THEN** el entrevistador conduce la etapa en inglés y el scorecard y el debrief se redactan en inglés

#### Scenario: Todo en español
- **WHEN** el candidato inicia con `lang=es`
- **THEN** el resumen de configuración, la entrevista, los scorecards, el debrief y el plan de estudio se presentan en español

### Requirement: Loop por defecto según el rol
El catálogo SHALL definir un loop por defecto por rol en tres fases: screens, VO1 (general) y VO2 (específica del equipo). El sistema lo usará cuando se pida el "loop completo". Antes de empezar SHALL informar qué etapas y variantes incluye cada fase y cuáles quedan como opcionales.

#### Scenario: Loop completo de ML Engineer
- **WHEN** el rol es ML Engineer y se pide el loop completo
- **THEN** el resumen lista como screens `recruiter-screen`, `hm-screen` y `technical-screen`; como VO1 `coding`, `ml-system-design` y `culture`; como VO2 `ml-depth`, `project-deep-dive`, `partnership` y `hm-onsite`; y marca como opcionales las demás etapas, incluida `ai-assisted-coding`

#### Scenario: Loop completo de Research Scientist
- **WHEN** el rol es Research Scientist y se pide el loop completo
- **THEN** la VO1 incluye `presentation@research-talk`

#### Scenario: Loop completo de Applied/Data Scientist
- **WHEN** el rol es Applied/Data Scientist y se pide el loop completo
- **THEN** los screens incluyen `technical-screen@sql` y `technical-screen@stats`, y la VO1 incluye `presentation@take-home` y `experimentation`

### Requirement: Corte entre VO1 y VO2
Cuando una sesión incluye etapas de VO1 y de VO2, el sistema SHALL convocar al terminar la VO1 un debrief de corte que decida si se continúa a la VO2, como en el proceso real. El candidato SHALL poder seguir igualmente en modo práctica si el corte es negativo, y esa decisión queda registrada.

#### Scenario: Corte negativo
- **WHEN** el debrief de corte decide no continuar
- **THEN** el sistema muestra la decisión con su justificación y pregunta si se termina la sesión o se sigue con la VO2 en modo práctica

### Requirement: Selección de etapas a simular
El sistema SHALL permitir simular el loop por defecto del rol, una sola etapa, una sola fase (p. ej. solo VO1) o cualquier subconjunto del catálogo, incluidas etapas opcionales y variantes concretas (`stage@variant`). Con varias etapas, SHALL ejecutarlas en el orden canónico del catálogo, salvo que el candidato pida otro orden explícitamente.

#### Scenario: Una sola etapa
- **WHEN** el candidato elige solo `experimentation`
- **THEN** el sistema ejecuta únicamente esa etapa, emite su scorecard y no convoca el debrief

#### Scenario: Etapa opcional para el rol
- **WHEN** un ML Engineer elige `experimentation`, que no está en su loop por defecto
- **THEN** el sistema la ejecuta con la variante adecuada para el rol

#### Scenario: Subconjunto en orden propio
- **WHEN** el candidato elige `culture` y `coding` y pide hacer `culture` primero
- **THEN** el sistema ejecuta `culture` y luego `coding`

### Requirement: Transición entre etapas
Al terminar una etapa, el sistema SHALL anunciar el cierre, guardar su transcripción, lanzar su evaluación y preguntar al candidato si continúa con la siguiente etapa, pausa o termina la sesión.

#### Scenario: Continuar
- **WHEN** termina `coding` y quedan etapas pendientes
- **THEN** el sistema guarda la transcripción, ofrece continuar, pausar o terminar, y al elegir continuar presenta al entrevistador de la siguiente etapa

#### Scenario: Terminar antes de tiempo
- **WHEN** el candidato decide terminar con etapas pendientes
- **THEN** el sistema marca esas etapas como no realizadas, emite los scorecards de las completadas y, si hay dos o más, convoca el debrief indicando que el loop está incompleto

### Requirement: Pausa y reanudación
El sistema SHALL permitir pausar una sesión y reanudarla más tarde desde la siguiente etapa pendiente, aunque sea en otra conversación, siempre que los archivos locales de la sesión sigan existiendo.

#### Scenario: Reanudar sesión
- **WHEN** el candidato invoca `/netflix-ml-interview resume` y existe una sesión local con etapas pendientes
- **THEN** el sistema muestra la configuración y las etapas completadas y continúa desde la primera etapa pendiente

#### Scenario: Nada que reanudar
- **WHEN** el candidato pide reanudar y no hay sesiones locales con etapas pendientes
- **THEN** el sistema lo indica y ofrece iniciar una sesión nueva

### Requirement: Comandos del candidato durante la sesión
Durante una etapa, el sistema SHALL reconocer los comandos `/pause`, `/end-stage` y `/time` como instrucciones al orquestador y no como respuestas al entrevistador.

#### Scenario: Consultar tiempo
- **WHEN** el candidato escribe `/time` en mitad de una etapa
- **THEN** el sistema muestra el tiempo transcurrido y el presupuesto de la etapa sin que el entrevistador lo trate como respuesta

#### Scenario: Terminar etapa
- **WHEN** el candidato escribe `/end-stage`
- **THEN** el entrevistador cierra la etapa y el sistema pasa a la transición como en un cierre normal
