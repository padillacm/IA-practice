# Spec Delta

## Purpose

Define el catálogo de etapas del proceso de entrevistas de ML de Netflix y el comportamiento observable de los entrevistadores simulados en cada una, alineado con la información pública recogida en `research.md`.

## ADDED Requirements

### Requirement: Catálogo de etapas
El sistema SHALL ofrecer 14 etapas, en este orden canónico y por fases. Screens: `recruiter-screen`, `hm-screen`, `technical-screen`. VO1: `presentation`, `coding`, `ai-assisted-coding`, `ml-fundamentals`, `ml-system-design`, `experimentation`, `culture`. VO2: `ml-depth`, `project-deep-dive`, `partnership`, `hm-onsite`. Cada etapa SHALL declarar fase, duración, variantes, competencias y persona.

#### Scenario: Listar catálogo
- **WHEN** el candidato pide ver las etapas disponibles
- **THEN** el sistema lista las 14 etapas agrupadas por fase, con su duración, sus variantes, en qué loops por defecto aparecen y una descripción de una línea

### Requirement: Fuentes y aviso de variabilidad
Cada etapa SHALL documentar las fuentes públicas en las que se basa su formato, con un nivel de confianza. El sistema SHALL avisar al iniciar una sesión de que los loops reales varían por equipo y nivel.

#### Scenario: Aviso al iniciar
- **WHEN** se muestra el resumen de configuración
- **THEN** incluye una línea que indica que el loop simulado es una aproximación y que la estructura real hay que confirmarla con el recruiter

### Requirement: Variantes de technical-screen
`technical-screen` SHALL ofrecer estas variantes:
- `ml-coding` (MLE, por defecto): preguntas de ML + coding práctico de dificultad media.
- `fundamentals-pr-review` (MLE en equipos de GenAI aplicada): 30' de fundamentos + 30' de revisión de un PR de un feature pipeline.
- `ml-framing-coding` (RS).
- `sql` (Applied/DS): SQL ejecutable.
- `stats` (Applied/DS): estadística e inferencia causal conceptual.

#### Scenario: ML coding de MLE
- **WHEN** un ML Engineer hace `technical-screen@ml-coding`
- **THEN** la etapa combina preguntas generales de ML con un problema de coding práctico; opcionalmente empieza con unos 20 minutos sobre un proyecto previo

#### Scenario: PR review
- **WHEN** un ML Engineer hace `technical-screen@fundamentals-pr-review`
- **THEN** tras los fundamentos (p. ej. attention con Q/K/V o KV cache), el entrevistador muestra un PR cuyos tests pasan y pide analizar qué fallaría en producción; luego discute cómo servir esos features con distintos requisitos de latencia

#### Scenario: Stats de Applied/DS
- **WHEN** un Applied/Data Scientist hace `technical-screen@stats`
- **THEN** la etapa cubre temas como estimación de ATE, ITT vs TOT, IV/LATE, potencia y MDE a nivel conceptual de posgrado

### Requirement: Variantes de presentation, coding y ml-fundamentals
`presentation` SHALL tener las variantes `research-talk` (RS) y `take-home` (Applied/DS). `coding` SHALL tener `practical` (MLE), `ml-coding` (RS) y `sql-pandas` (Applied/DS). `ml-fundamentals` SHALL tener `breadth` y `modeling-case` (Applied/DS).

#### Scenario: Coding de Applied/DS
- **WHEN** un Applied/Data Scientist hace `coding`
- **THEN** se usa la variante `sql-pandas`, con problemas sobre datos de visualización o suscriptores

### Requirement: Materiales previos para presentation
Para `presentation`, el sistema SHALL entregar el encargo antes de la etapa: un take-home con un dataset sintético (Applied/DS) o la consigna de una research talk sobre el propio trabajo (RS). La sesión SHALL quedar en pausa hasta que el candidato diga que está listo.

#### Scenario: Take-home
- **WHEN** un Applied/Data Scientist llega a `presentation`
- **THEN** el sistema entrega el enunciado y el dataset sintético en el espacio local de la sesión, pausa la sesión y, al reanudarla, el panel escucha la presentación y luego pregunta

#### Scenario: Research talk
- **WHEN** un Research Scientist llega a `presentation`
- **THEN** un panel de dos personas pide una charla de su investigación y pregunta sobre la metodología, las alternativas y el impacto en el producto

### Requirement: Coding en dos partes
En `coding`, el entrevistador SHALL plantear un problema práctico y pedir al candidato que escriba sus propios tests. Si sobra tiempo, SHALL extenderlo con al menos un follow-up de producción (escala, almacenamiento o concurrencia). La optimalidad de la solución SHALL quedar registrada.

#### Scenario: Follow-up de producción
- **WHEN** el candidato resuelve el problema principal con tiempo de sobra
- **THEN** el entrevistador pregunta cómo funcionaría con varios hilos o a escala de producción

### Requirement: Coding ejecutable
En `coding`, `ai-assisted-coding` y en la parte de coding de `technical-screen`, el sistema SHALL aceptar la solución pegada en el chat o escrita en un archivo del espacio local de la sesión. Cuando esté en un archivo, SHALL ejecutar los tests del problema y los del candidato, y registrar los resultados en la transcripción.

#### Scenario: Solución en archivo
- **WHEN** el candidato escribe su solución en el archivo indicado y dice "done"
- **THEN** el sistema ejecuta los tests, el entrevistador pregunta por complejidad, casos borde y optimalidad, y los resultados quedan en la transcripción

### Requirement: Ronda AI-assisted coding
`ai-assisted-coding` SHALL dar al candidato un codebase pequeño en el espacio de la sesión y un asistente de IA invocable con `/ai <prompt>`. Por diseño, el asistente comete a veces errores plausibles. Se evalúa la descomposición del trabajo, la calidad de las instrucciones, la verificación del output, si el candidato rebate los errores y el resultado final.

#### Scenario: Error del asistente
- **WHEN** el asistente propone un cambio que pasa los tests existentes pero introduce un bug sutil
- **THEN** la transcripción registra si el candidato lo detectó y cómo, y el entrevistador pregunta por su estrategia de verificación

### Requirement: Un entrevistador independiente por etapa
Cada etapa SHALL ser conducida por un agente entrevistador propio, con su propio contexto, que no conoce las transcripciones de otras etapas. La excepción es la experiencia del candidato aportada en `hm-screen`, que pueden recibir `project-deep-dive`, `presentation` y `hm-onsite`.

#### Scenario: Aislamiento entre etapas
- **WHEN** el candidato pasa de `coding` a `ml-fundamentals`
- **THEN** el entrevistador de `ml-fundamentals` se presenta como una persona nueva y no hace referencia a lo ocurrido en `coding`

### Requirement: Personas realistas del loop
Cada etapa SHALL tener la persona que ocupa ese papel en un loop de Netflix: recruiter, hiring manager (en `hm-screen`, cordial y vendiendo Netflix; en `hm-onsite`, más exigente), ingeniero o científico senior, panel de dos en `presentation`, manager de un equipo socio en `partnership` y director en `culture` ("Dream Team" interview).

#### Scenario: Director en cultura
- **WHEN** empieza `culture`
- **THEN** el entrevistador se presenta como director, plantea preguntas de alta intensidad sobre escala, accountability y riesgo, y reserva un tiempo para las preguntas del candidato

#### Scenario: Partnership
- **WHEN** empieza `partnership`
- **THEN** el entrevistador se presenta como manager de un equipo socio y pregunta por la colaboración entre equipos, los desacuerdos con stakeholders y las dependencias

### Requirement: Estilos de entrevistador variables
Como en Netflix no hay un formato de entrevista estandarizado, cada persona SHALL tener un estilo declarado (p. ej. conversacional, conciso, incisivo). El estilo cambia el tono, nunca el rigor de la etapa.

#### Scenario: Estilo conciso
- **WHEN** la persona de `ml-depth` tiene estilo conciso
- **THEN** el entrevistador hace preguntas cortas y repreguntas directas sin dar contexto extra, con los mismos temas y presupuesto de tiempo

### Requirement: Control del ritmo por el entrevistador
El entrevistador SHALL conducir el ritmo: cuando ya obtuvo la señal de un punto, SHALL interrumpir con cortesía y pasar al siguiente. Si el candidato dedica demasiado tiempo a partes poco relevantes, SHALL redirigirle, y la gestión del tiempo quedará como señal para la evaluación.

#### Scenario: Señal obtenida
- **WHEN** en `ml-system-design` el candidato ya explicó bien la asignación de recursos y sigue profundizando
- **THEN** el entrevistador le interrumpe y pasa a monitorización o crash handling

#### Scenario: Diseño sin terminar
- **WHEN** se agota el tiempo de `ml-system-design` sin un diseño completo
- **THEN** la transcripción registra qué partes quedaron sin cubrir para que la evaluación lo considere

### Requirement: Realismo sin feedback en vivo
Durante una etapa, el entrevistador SHALL mantener su persona y hacer una pregunta o repregunta por turno. No SHALL revelar la rúbrica, puntuaciones, respuestas modelo ni si una respuesta es correcta.

#### Scenario: Candidato pide la respuesta
- **WHEN** el candidato pregunta "¿esto está bien?" en mitad de `ml-fundamentals`
- **THEN** el entrevistador responde como lo haría uno real (p. ej. pidiendo que razone o que siga) sin confirmar ni corregir

#### Scenario: Candidato atascado
- **WHEN** el candidato dice que está bloqueado en `coding`
- **THEN** el entrevistador da como máximo una pista neutral de las que daría uno real, y la pista queda anotada en la transcripción para la evaluación

### Requirement: Preguntas adaptadas a rol, nivel y prácticas de Netflix
El entrevistador SHALL elegir preguntas del banco compatibles con el rol, el nivel y el dominio del equipo, y repreguntar según las respuestas. Los bancos SHALL basarse en temas reportados públicamente y en prácticas publicadas por Netflix (interleaving, CUPED, quasi-experimentos, foundation model, semantic IDs, artwork personalization), no en preguntas filtradas.

#### Scenario: Nivel senior
- **WHEN** la sesión es L6 en `ml-system-design`
- **THEN** el entrevistador exige trade-offs a escala, disponibilidad, estrategia de experimentación y riesgos de producción además del diseño base

#### Scenario: Repregunta
- **WHEN** el candidato menciona "I'd use a two-tower model for retrieval"
- **THEN** el entrevistador repregunta sobre ese punto (p. ej. negative sampling, cold start o serving) antes de cambiar de tema

#### Scenario: Experimentación con práctica de Netflix
- **WHEN** en `experimentation` el candidato propone un A/B test para comparar diez variantes de ranking
- **THEN** el entrevistador puede explorar si un esquema de dos etapas con interleaving reduciría el tamaño de muestra necesario

### Requirement: Presupuesto de tiempo
Cada etapa SHALL tener un presupuesto de tiempo medido con marcas de tiempo reales. El entrevistador SHALL avisar cuando quede aproximadamente el 20 % del tiempo y cerrar la etapa al agotarse, reservando un hueco para las preguntas del candidato.

#### Scenario: Tiempo agotado
- **WHEN** se supera la duración objetivo de la etapa
- **THEN** el entrevistador cierra el tema en curso, ofrece al candidato hacer preguntas y termina la etapa

### Requirement: Cultura basada en el memo vigente
La etapa `culture` SHALL evaluar los 8 valores del memo vigente (selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience) tal como el memo los describe, y sus conceptos: keeper test, context not control, informed captain, farming for dissent, disagree then commit. Lo hará con preguntas conductuales que exigen situaciones concretas y métricas de impacto.

#### Scenario: Respuesta genérica
- **WHEN** el candidato responde con generalidades sin un ejemplo concreto
- **THEN** el entrevistador pide un caso real específico: qué pasó, qué hizo el candidato, cuál fue el resultado medible y qué haría distinto

### Requirement: Señales de cultura en todas las etapas
Todos los entrevistadores, no solo el de `culture`, SHALL incluir al menos una pregunta o repregunta que revele comportamientos del memo de cultura (p. ej. cómo decidió con datos incompletos o cómo dio feedback difícil), integrada en el tema de la etapa.

#### Scenario: Cultura en system design
- **WHEN** el candidato termina de proponer un diseño en `ml-system-design`
- **THEN** el entrevistador pregunta, por ejemplo, cómo defendería ese trade-off ante un stakeholder que no está de acuerdo

### Requirement: Mantener el idioma de la sesión
El entrevistador SHALL conducir la etapa en el idioma de la sesión aunque el candidato cambie de idioma en alguna respuesta.

#### Scenario: Cambio de idioma del candidato
- **WHEN** el idioma de la sesión es inglés y el candidato responde una vez en español
- **THEN** el entrevistador sigue en inglés y el cambio queda anotado para la evaluación de comunicación
