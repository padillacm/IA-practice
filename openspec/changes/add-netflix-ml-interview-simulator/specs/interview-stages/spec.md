# Spec Delta

## Purpose

Define el catálogo de etapas del proceso de entrevistas de ML de Netflix y el comportamiento observable de los entrevistadores simulados en cada una, alineado con la información pública recogida en `research.md`.

## ADDED Requirements

### Requirement: Catálogo de etapas
El sistema SHALL ofrecer 11 etapas, en este orden canónico: `recruiter-screen`, `hiring-manager`, `technical-screen`, `presentation`, `coding`, `ml-fundamentals`, `ml-system-design`, `ml-depth`, `experimentation`, `project-deep-dive`, `culture`. Cada etapa SHALL declarar su fase (screen o loop final), la duración objetivo, las variantes por rol, las competencias y la persona del entrevistador.

#### Scenario: Listar catálogo
- **WHEN** el candidato pide ver las etapas disponibles
- **THEN** el sistema lista las 11 etapas con su fase, duración, en qué loops por defecto aparecen y una descripción de una línea

### Requirement: Fuentes y aviso de variabilidad
Cada etapa SHALL documentar las fuentes públicas en las que se basa su formato, con un nivel de confianza. El sistema SHALL avisar al iniciar una sesión de que los loops reales varían por equipo y nivel.

#### Scenario: Aviso al iniciar
- **WHEN** se muestra el resumen de configuración
- **THEN** incluye una línea que indica que el loop simulado es una aproximación y que la estructura real hay que confirmarla con el recruiter

### Requirement: Variantes por rol
Las etapas `technical-screen`, `presentation`, `coding` y `ml-fundamentals` SHALL tener variantes por rol. `technical-screen`: proyecto previo + ML coding (MLE), estadística/ML + coding breve (RS), SQL + caso (Applied/DS). `presentation`: research talk (RS) o take-home readout (Applied/DS). `coding`: Python práctico o algorítmico (MLE/RS) o SQL/pandas (Applied/DS). `ml-fundamentals`: caso de modelado (Applied/DS).

#### Scenario: Technical screen de MLE
- **WHEN** un ML Engineer hace `technical-screen`
- **THEN** la etapa dedica unos 20 minutos a un proyecto previo y unos 40 a un problema de ML coding práctico (p. ej. una métrica de ranking o similitud sobre datos de interacción)

#### Scenario: Technical screen de Applied/DS
- **WHEN** un Applied/Data Scientist hace `technical-screen`
- **THEN** la etapa plantea SQL sobre un esquema de datos de visualización o suscriptores y un caso analítico corto

### Requirement: Materiales previos para presentation
Para `presentation`, el sistema SHALL entregar al candidato el encargo antes de la etapa: un take-home con un dataset sintético para Applied/DS, o la consigna de una research talk sobre su propio trabajo para RS. La sesión SHALL quedar en pausa hasta que el candidato diga que está listo.

#### Scenario: Take-home
- **WHEN** un Applied/Data Scientist llega a `presentation`
- **THEN** el sistema entrega el enunciado y el dataset sintético en el espacio local de la sesión, pausa la sesión y al reanudarla el panel escucha la presentación y luego pregunta

#### Scenario: Research talk
- **WHEN** un Research Scientist llega a `presentation`
- **THEN** el panel pide una charla de su investigación y hace preguntas de fondo sobre metodología, alternativas y su impacto en el producto

### Requirement: Un entrevistador independiente por etapa
Cada etapa SHALL ser conducida por un agente entrevistador propio, con su propio contexto, que no conoce las transcripciones de otras etapas. La excepción es la información sobre la experiencia del candidato aportada en `hiring-manager`, que pueden recibir `project-deep-dive` y `presentation`.

#### Scenario: Aislamiento entre etapas
- **WHEN** el candidato pasa de `coding` a `ml-fundamentals`
- **THEN** el entrevistador de `ml-fundamentals` se presenta como una persona nueva y no hace referencia a lo ocurrido en `coding`

### Requirement: Personas realistas del loop
Cada etapa SHALL tener la persona que ocupa ese papel en un loop de Netflix: recruiter, hiring manager, ingeniero/científico senior del equipo, panel de dos personas en `presentation` y director (de la organización que contrata o de una socia) en `culture`.

#### Scenario: Director en cultura
- **WHEN** empieza `culture`
- **THEN** el entrevistador se presenta como director y orienta la conversación al juicio, el impacto y la colaboración entre equipos

### Requirement: Realismo sin feedback en vivo
Durante una etapa, el entrevistador SHALL mantener su persona y hacer una pregunta o repregunta por turno. No SHALL revelar la rúbrica, puntuaciones, respuestas modelo ni si una respuesta es correcta.

#### Scenario: Candidato pide la respuesta
- **WHEN** el candidato pregunta "¿esto está bien?" en mitad de `ml-fundamentals`
- **THEN** el entrevistador responde como lo haría uno real (p. ej. pidiendo que razone o que siga) sin confirmar ni corregir

#### Scenario: Candidato atascado
- **WHEN** el candidato dice que está bloqueado en `coding`
- **THEN** el entrevistador da como máximo una pista neutral de las que daría uno real y la pista queda anotada en la transcripción para la evaluación

### Requirement: Preguntas adaptadas a rol, nivel y prácticas de Netflix
El entrevistador SHALL elegir preguntas del banco compatibles con el rol y el nivel y repreguntar según las respuestas. Los bancos SHALL basarse en temas reportados públicamente y en prácticas documentadas por Netflix (p. ej. interleaving, CUPED, quasi-experimentos, personalización de artwork, foundation model de recomendación), no en preguntas filtradas.

#### Scenario: Nivel senior
- **WHEN** la sesión es L6 en `ml-system-design`
- **THEN** el entrevistador exige trade-offs a escala, estrategia de experimentación y riesgos de producción además del diseño base

#### Scenario: Repregunta
- **WHEN** el candidato menciona "I'd use a two-tower model for retrieval"
- **THEN** el entrevistador repregunta sobre ese punto (p. ej. negative sampling, cold start o serving) antes de cambiar de tema

#### Scenario: Experimentación con práctica de Netflix
- **WHEN** en `experimentation` el candidato propone un A/B test para comparar diez variantes de ranking
- **THEN** el entrevistador puede explorar si un esquema de dos etapas con interleaving reduciría el tamaño de muestra necesario

### Requirement: Presupuesto de tiempo
Cada etapa SHALL tener un presupuesto de tiempo medido con marcas de tiempo reales. El entrevistador SHALL avisar cuando quede aproximadamente el 20 % del tiempo y cerrar la etapa al agotarse, reservando un hueco para preguntas del candidato.

#### Scenario: Tiempo agotado
- **WHEN** se supera la duración objetivo de la etapa
- **THEN** el entrevistador cierra el tema en curso, ofrece al candidato hacer preguntas y termina la etapa

### Requirement: Coding ejecutable
En `coding` y en la parte de coding de `technical-screen`, el sistema SHALL aceptar la solución pegada en el chat o escrita en un archivo del espacio local de la sesión. Cuando esté en un archivo, SHALL ejecutar los tests del problema y registrar el resultado en la transcripción.

#### Scenario: Solución en archivo
- **WHEN** el candidato escribe su solución en el archivo indicado y dice "done"
- **THEN** el sistema ejecuta los tests, el entrevistador pregunta por complejidad, casos borde y optimalidad, y el resultado queda en la transcripción

### Requirement: Cultura basada en el memo vigente
La etapa `culture` SHALL evaluar los valores del memo de cultura vigente de Netflix (selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience) y sus conceptos (keeper test, context not control, informed captain, farming for dissent, disagree and commit). Lo hará con preguntas conductuales que exigen situaciones concretas.

#### Scenario: Respuesta genérica
- **WHEN** el candidato responde con generalidades sin un ejemplo concreto
- **THEN** el entrevistador pide un caso real específico: qué pasó, qué hizo el candidato y cuál fue el resultado

### Requirement: Señales de cultura en todas las etapas
Todos los entrevistadores, no solo el de `culture`, SHALL incluir al menos una pregunta o repregunta que revele comportamientos del memo de cultura (p. ej. cómo decidió con datos incompletos o cómo dio feedback difícil), integrada en el tema técnico de la etapa.

#### Scenario: Cultura en system design
- **WHEN** el candidato termina de proponer un diseño en `ml-system-design`
- **THEN** el entrevistador pregunta, por ejemplo, cómo defendería ese trade-off ante un stakeholder que no está de acuerdo

### Requirement: Mantener el idioma de la sesión
El entrevistador SHALL conducir la etapa en el idioma de la sesión aunque el candidato cambie de idioma en alguna respuesta.

#### Scenario: Cambio de idioma del candidato
- **WHEN** el idioma de la sesión es inglés y el candidato responde una vez en español
- **THEN** el entrevistador sigue en inglés y el cambio queda anotado para la evaluación de comunicación
