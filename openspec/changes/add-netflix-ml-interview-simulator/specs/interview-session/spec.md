# Spec Delta

## Purpose

Permite al candidato configurar y conducir una sesión de entrevista simulada de Netflix para roles de ML, eligiendo rol, nivel, idioma y qué etapas practicar, y orquesta el paso entre etapas y fases.

## ADDED Requirements

### Requirement: Inicio de sesión con configuración explícita
El sistema SHALL iniciar cada sesión con estos valores, pedidos al candidato o recibidos como argumentos: rol (`mle`, `rs`, `ds`), nivel (L4, L5 o L6; L5 por defecto), idioma, etapas, dominio del equipo, modo de feedback (inmediato o diferido), `time_scale` y, opcionalmente, un archivo de background del candidato. No SHALL comenzar ninguna etapa hasta que el candidato confirme el resumen.

#### Scenario: Configuración interactiva
- **WHEN** el candidato invoca `/netflix-ml-interview` sin argumentos
- **THEN** el sistema pregunta los valores que faltan, propone los valores por defecto, muestra el resumen y espera confirmación

#### Scenario: Configuración por argumentos
- **WHEN** el candidato invoca `/netflix-ml-interview role=mle stages=ml-system-design`
- **THEN** el sistema usa los valores por defecto para el resto (L5, inglés, dominio recsys, feedback inmediato, `time_scale` 1.5), muestra el resumen y pide confirmación

#### Scenario: Valor inválido
- **WHEN** el candidato indica una etapa, variante, rol, nivel, dominio o idioma que no existe, o una variante incompatible con el rol (p. ej. `coding@foo`)
- **THEN** el sistema rechaza el valor, lista las opciones válidas y no inicia la sesión

### Requirement: Roles y su equivalencia
El rol `rs` SHALL cubrir Research Scientist, ML Scientist y Applied Scientist, y `ds` SHALL ser "Data Scientist (experimentation & analytics)". El resumen SHALL indicar a qué rol corresponde cada título.

#### Scenario: Applied Scientist
- **WHEN** el candidato dice que su puesto es "Applied Scientist"
- **THEN** el sistema propone el rol `rs` y explica que `ds` es el track de experimentación y analítica

### Requirement: Background del candidato
Si el candidato aporta un archivo de background (CV o proyectos), el sistema SHALL extraer de él un perfil de candidato y entregarlo a todos los entrevistadores. Si no lo aporta, el perfil SHALL construirse a partir de lo que diga en `hm-screen`, cuando esa etapa se haga.

#### Scenario: Sin background ni hm-screen
- **WHEN** el candidato hace solo `project-deep-dive` sin aportar background
- **THEN** el entrevistador empieza pidiéndole que resuma el proyecto que quiere discutir

### Requirement: Idioma único de la sesión
El idioma por defecto SHALL ser inglés en toda la sesión: configuración, entrevista, scorecards, debrief y plan de estudio. Con `lang=es`, todo ello SHALL ser en español. Los términos técnicos estándar y los enums de los archivos se mantienen en inglés en ambos modos.

#### Scenario: Por defecto en inglés
- **WHEN** el candidato no indica idioma
- **THEN** la entrevista, el scorecard y el debrief están en inglés

#### Scenario: Todo en español
- **WHEN** el candidato inicia con `lang=es`
- **THEN** la configuración, la entrevista, los scorecards, el debrief y el plan de estudio están en español

### Requirement: Loop por defecto según el rol
El catálogo SHALL definir para cada rol un loop por defecto en tres fases (screen, VO1, VO2), con la variante de cada entrada, y SHALL indicar si el rol tiene corte entre VO1 y VO2. El sistema lo usará cuando se pida el "loop completo" e informará antes de empezar de las etapas de cada fase y de las opcionales.

#### Scenario: Loop completo de ML Engineer
- **WHEN** el rol es `mle` y se pide el loop completo
- **THEN** el resumen muestra:
  - screens: `recruiter-screen`, `hm-screen` y `technical-screen@ml-coding`;
  - VO1: `coding@practical`, `ml-system-design@design` y `culture`;
  - VO2: `ml-depth`, `project-deep-dive`, `partnership` y `hm-onsite`;
  - el corte activado.

#### Scenario: Loop completo de Research Scientist
- **WHEN** el rol es `rs` y se pide el loop completo
- **THEN** la VO1 incluye `presentation@research-talk` y `ml-system-design@problem-framing`, y el corte aparece desactivado

#### Scenario: Loop completo de Data Scientist
- **WHEN** el rol es `ds` y se pide el loop completo
- **THEN** los screens incluyen `technical-screen@sql` y `technical-screen@stats`, la VO1 incluye `experimentation@design-case` y `experimentation@analysis-case`, y el dominio por defecto es experimentation

### Requirement: Instancias de etapa
Cada ejecución de una etapa en una sesión SHALL tener un id de instancia único (`NN-<stage>@<variant>`) que identifique su agente, su transcripción, su scorecard y su estado. Así la misma etapa puede aparecer varias veces en una sesión.

#### Scenario: Dos technical screens
- **WHEN** una sesión de `ds` ejecuta `technical-screen@sql` y `technical-screen@stats`
- **THEN** cada una tiene su propia transcripción y su propio scorecard, sin colisiones

### Requirement: Selección de etapas a simular
El sistema SHALL permitir simular el loop por defecto, una sola fase (`stages=vo1`), una sola etapa o cualquier subconjunto, con variantes concretas (`stage@variant`) y etapas opcionales. Una etapa sin variante explícita SHALL usar la variante por defecto del rol. El orden SHALL ser el canónico (fase y luego catálogo), salvo que el candidato pida otro.

#### Scenario: Una sola etapa
- **WHEN** el candidato elige solo `experimentation`
- **THEN** el sistema ejecuta esa etapa, emite su scorecard y no convoca el debrief

#### Scenario: Etapa opcional para el rol
- **WHEN** un `mle` elige `ml-fundamentals`
- **THEN** el sistema usa la variante `breadth`

#### Scenario: Una fase
- **WHEN** el candidato elige `stages=vo1` con rol `mle`
- **THEN** el sistema ejecuta `coding@practical`, `ml-system-design@design` y `culture`, en ese orden

### Requirement: Listar el catálogo
El sistema SHALL mostrar el catálogo con `/netflix-ml-interview stages`, sin iniciar ninguna sesión.

#### Scenario: Listado
- **WHEN** el candidato invoca `/netflix-ml-interview stages`
- **THEN** el sistema lista las etapas por fase, con duración, variantes y en qué loops por defecto aparecen

### Requirement: Transición y corte entre fases
Al terminar una etapa, el sistema SHALL guardar su transcripción, obtener su scorecard según el modo de feedback y ofrecer continuar, pausar o terminar. Si el rol tiene corte activo y la sesión incluye VO1 y VO2, al terminar la VO1 SHALL convocar el debrief de corte. Si el corte es negativo, SHALL ofrecer terminar o seguir en modo práctica.

#### Scenario: Corte negativo
- **WHEN** el debrief de corte decide no continuar
- **THEN** el sistema muestra la decisión y pregunta si se termina o se sigue con la VO2 en modo práctica, y lo registra en la sesión

#### Scenario: Terminar antes de tiempo
- **WHEN** el candidato decide terminar con etapas pendientes
- **THEN** el sistema marca esas etapas como no realizadas y, si hay dos o más completadas, convoca el debrief indicando que el loop está incompleto

### Requirement: Pausa y reanudación
El sistema SHALL permitir pausar y reanudar en otra conversación mientras existan los archivos locales. Si la instancia estaba en curso, SHALL reconstruir al entrevistador a partir de la transcripción, con la misma persona y sin volver a presentarse. Si hay varias sesiones pendientes, SHALL listarlas para elegir.

#### Scenario: Reanudar una etapa en curso
- **WHEN** el candidato invoca `/netflix-ml-interview resume` y la última instancia quedó en curso
- **THEN** un entrevistador reconstruido con la transcripción y el tiempo restante responde al último mensaje del candidato

#### Scenario: Nada que reanudar
- **WHEN** el candidato pide reanudar y no hay sesiones locales pendientes
- **THEN** el sistema lo indica y ofrece iniciar una sesión nueva

### Requirement: Comandos del candidato durante la sesión
Durante una etapa, el sistema SHALL reconocer los comandos con prefijo `::` como instrucciones al orquestador y no como respuestas al entrevistador: `::time`, `::pause`, `::end`, `::ai <prompt>`, `::apply` y `::help`. El prefijo `::` evita el conflicto con los slash commands de la CLI.

#### Scenario: Consultar tiempo
- **WHEN** el candidato escribe `::time` en mitad de una etapa
- **THEN** el sistema muestra el tiempo transcurrido y el presupuesto, y el entrevistador no lo recibe como respuesta

#### Scenario: Pausar
- **WHEN** el candidato escribe `::pause`
- **THEN** el reloj de la etapa se detiene, el estado se guarda y el sistema indica cómo reanudar

#### Scenario: Comando desconocido
- **WHEN** el candidato escribe `::foo`
- **THEN** el sistema muestra `::help` y no envía nada al entrevistador

### Requirement: Modo degradado
Si el canal para enviar mensajes a un subagente no está disponible, el sistema SHALL avisar y conducir la etapa en el hilo principal con la persona del entrevistador. La evaluación SHALL seguir haciéndola un agente separado, y el modo degradado SHALL quedar registrado.

#### Scenario: Sin canal de mensajes
- **WHEN** no se puede reanudar al entrevistador mediante mensajes
- **THEN** el sistema avisa, continúa en modo degradado y la sesión queda marcada como degradada
