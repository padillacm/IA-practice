# Spec Delta

## Purpose

Define el catálogo de etapas del proceso de entrevistas de ML de Netflix y el comportamiento observable de los entrevistadores simulados en cada una, alineado con la información pública recogida en `research.md`.

## ADDED Requirements

### Requirement: Catálogo de etapas
El sistema SHALL ofrecer 14 etapas: `recruiter-screen`, `hm-screen`, `technical-screen`, `presentation`, `coding`, `ai-assisted-coding`, `ml-fundamentals`, `ml-system-design`, `experimentation`, `culture`, `ml-depth`, `project-deep-dive`, `partnership` y `hm-onsite`. De cada una SHALL declarar fase por defecto, duración, variantes con su valor por defecto por rol, competencias, persona y estilo.

#### Scenario: Validación del catálogo
- **WHEN** se ejecuta la validación del simulador
- **THEN** las 14 etapas tienen todos sus campos, y cada entrada de los loops apunta a una etapa y una variante existentes y compatibles con el rol

### Requirement: Fuentes y aviso de variabilidad
Cada etapa SHALL documentar las fuentes públicas en que se basa, con su nivel de confianza, y marcar como supuestos las duraciones y los descriptores de nivel extrapolados. Al iniciar una sesión, el sistema SHALL avisar de que los loops reales varían por equipo y nivel.

#### Scenario: Aviso al iniciar
- **WHEN** se muestra el resumen de configuración
- **THEN** incluye una línea que indica que el loop simulado es una aproximación y que la estructura real hay que confirmarla con el recruiter

### Requirement: Variantes de technical-screen
`technical-screen` SHALL ofrecer:
- `ml-coding` (MLE): unos 20' de preguntas de ML y unos 40' de coding práctico de dificultad media.
- `ml-framing-coding` (RS).
- `sql` y `stats` (DS).
- Opcionales: `fundamentals-pr-review`, `intern-project-coding` (20' de proyecto + 40' de coding, formato reportado en prácticas) y `oa`.

#### Scenario: PR review
- **WHEN** un `mle` hace `technical-screen@fundamentals-pr-review`
- **THEN** tras los fundamentos (p. ej. attention con Q/K/V o KV cache), el entrevistador muestra un PR cuyos tests pasan y pide analizar qué fallaría en producción; después discute cómo servir esos features con distintas latencias

#### Scenario: Stats de DS
- **WHEN** un `ds` hace `technical-screen@stats`
- **THEN** la etapa cubre interpretación de regresión, errores tipo I/II, pruebas múltiples y FDR, CLT y t-stat, bootstrap, potencia y MDE y, opcionalmente, inferencia causal (ATE, IV/LATE)

### Requirement: Variantes de las etapas del onsite
Las etapas del onsite SHALL tener estas variantes:
- `presentation`: `research-talk` (RS, 45') y `take-home` (DS).
- `coding`: `practical` (MLE), `ml-coding` (RS), `sql-pandas` (DS) y `lc-style` (opcional).
- `ml-fundamentals`: `breadth` y `modeling-case` (DS, opcional, sin evidencia directa).
- `ml-system-design`: `design` (MLE) y `problem-framing` (RS).
- `experimentation`: `design-case` y `analysis-case`.

#### Scenario: Experimentación de DS
- **WHEN** un `ds` hace el loop completo
- **THEN** la VO1 incluye un caso de diseño de experimento y otro de análisis de resultados (cuantiles, efectos heterogéneos, ajuste por covariables)

### Requirement: Materiales previos para presentation
Para `presentation`, el sistema SHALL entregar el encargo antes de la etapa: un take-home con dataset sintético (DS) o la consigna de una research talk sobre el propio trabajo (RS). La sesión SHALL quedar en pausa hasta que el candidato diga que está listo.

#### Scenario: Take-home
- **WHEN** un `ds` llega a `presentation`
- **THEN** el sistema genera el enunciado y el dataset en el espacio local de la sesión, pausa y, al reanudar, el panel escucha la presentación y luego pregunta

### Requirement: Coding en dos partes
En `coding`, el entrevistador SHALL plantear un problema práctico y pedir al candidato que escriba sus propios tests. Si sobra tiempo, SHALL extenderlo con al menos un follow-up de producción: escala, almacenamiento o concurrencia. La optimalidad de la solución SHALL quedar registrada.

#### Scenario: Follow-up de producción
- **WHEN** el candidato resuelve el problema principal con tiempo de sobra
- **THEN** el entrevistador pregunta cómo funcionaría con varios hilos o a escala de producción

### Requirement: Coding ejecutable
En `coding`, en `ai-assisted-coding` y en la parte de coding de `technical-screen`, el sistema SHALL aceptar la solución pegada en el chat o escrita en un archivo del espacio local de la sesión. Si está en un archivo, el orquestador (no el entrevistador) SHALL ejecutar los tests del problema y los del candidato, a la vista del candidato, y pasarle el resultado al entrevistador.

#### Scenario: Solución en archivo
- **WHEN** el candidato escribe su solución en el archivo indicado y dice "done"
- **THEN** se ejecutan los tests, el resultado queda en la transcripción y el entrevistador pregunta por complejidad, casos borde y optimalidad

### Requirement: Ronda AI-assisted coding
`ai-assisted-coding` SHALL dar al candidato un codebase pequeño y un asistente de IA invocable con `::ai <prompt>`. El asistente devuelve propuestas sin aplicarlas, y `::apply` las aplica. Por diseño, puede cometer entre 0 y 2 errores plausibles por repo. Se evalúan la descomposición del trabajo, las instrucciones, la verificación, la capacidad de rebatir los errores y el resultado.

#### Scenario: Error del asistente
- **WHEN** el asistente propone un cambio que pasa los tests existentes pero introduce un bug sutil
- **THEN** la transcripción registra si el candidato lo detectó, y el entrevistador pregunta por su estrategia de verificación sin revelar el error

### Requirement: Un entrevistador independiente por etapa
Cada instancia SHALL estar conducida por un agente propio, con contexto propio, que no conoce las transcripciones de otras etapas. Todos reciben el mismo perfil del candidato (background o `hm-screen`), y cada entrevistador de deep dive se centra en una parte distinta de ese perfil.

#### Scenario: Aislamiento entre etapas
- **WHEN** el candidato pasa de `coding` a `ml-fundamentals`
- **THEN** el nuevo entrevistador se presenta como una persona nueva y no hace referencia a lo ocurrido en `coding`

### Requirement: Personas realistas del loop
Cada etapa SHALL tener la persona que ocupa ese papel en Netflix:
- recruiter;
- HM: cordial y vendiendo Netflix en `hm-screen`, exigente en `hm-onsite`;
- ingeniero o científico senior;
- panel de dos en `presentation`;
- manager o director de un equipo socio en `partnership`;
- director en `culture` ("Dream Team").

Los directores SHALL reservar tiempo para las preguntas del candidato.

#### Scenario: Director en cultura
- **WHEN** empieza `culture`
- **THEN** el entrevistador se presenta como director, hace preguntas intensas sobre escala, accountability y riesgo, y reserva tiempo para las preguntas del candidato

### Requirement: Estilos de entrevistador variables
Cada persona SHALL tener un estilo declarado (conversacional, conciso o incisivo), porque en Netflix las entrevistas no están estandarizadas. El estilo cambia el tono, no el rigor.

#### Scenario: Estilo conciso
- **WHEN** la persona de `ml-depth` tiene estilo conciso
- **THEN** hace preguntas cortas y repreguntas directas, con los mismos temas y el mismo presupuesto de tiempo

### Requirement: Contrato de turno del entrevistador
Cada turno del entrevistador SHALL terminar con exactamente un bloque visible para el candidato y un bloque de metadatos factuales, sin nada después. El entrevistador no SHALL escribir ni suponer respuestas del candidato, ni usar herramientas después de su primer turno.

#### Scenario: Turno mal formado
- **WHEN** una respuesta del entrevistador no trae los dos bloques
- **THEN** el orquestador le pide reformatearla una vez y, si vuelve a fallar, muestra el texto en bruto y lo marca en la transcripción

### Requirement: Control del ritmo por el entrevistador
El entrevistador SHALL interrumpir con cortesía y pasar al siguiente punto cuando ya tenga la señal del actual. Si el candidato se extiende en partes poco relevantes, SHALL redirigirle. Los puntos de señal que queden sin cubrir SHALL registrarse.

#### Scenario: Señal obtenida
- **WHEN** en `ml-system-design` el candidato ya explicó bien la asignación de recursos y sigue profundizando
- **THEN** el entrevistador le interrumpe y pasa a monitorización o crash handling

#### Scenario: Diseño sin terminar
- **WHEN** se agota el tiempo de `ml-system-design` sin un diseño completo
- **THEN** la transcripción registra qué puntos de señal quedaron sin cubrir

### Requirement: Realismo sin feedback en vivo
Durante una etapa, el entrevistador SHALL mantener su persona y hacer una pregunta o repregunta por turno. No SHALL revelar la rúbrica, las puntuaciones, respuestas modelo ni si una respuesta es correcta. Puede dar como máximo una pista por cada bloqueo, registrada con su nivel: nudge o substantive.

#### Scenario: Candidato pide la respuesta
- **WHEN** el candidato pregunta "¿esto está bien?" en mitad de `ml-fundamentals`
- **THEN** el entrevistador le pide que razone o que siga, sin confirmar ni corregir

#### Scenario: Candidato atascado
- **WHEN** el candidato dice que está bloqueado en `coding`
- **THEN** el entrevistador da como máximo una pista neutral y la registra con su nivel y la competencia afectada

### Requirement: Preguntas adaptadas a rol, nivel y dominio
El orquestador SHALL elegir preguntas o problemas del banco compatibles con el rol, el nivel, la variante y el dominio. Mientras queden alternativas, excluirá los ya usados en sesiones locales anteriores. Los bancos SHALL basarse en temas reportados públicamente y en prácticas publicadas por Netflix, sin preguntar cifras concretas de esas publicaciones.

#### Scenario: Segunda vez en coding
- **WHEN** el candidato repite `coding` con el mismo rol y nivel
- **THEN** el problema principal es distinto del de la vez anterior

#### Scenario: Nivel senior
- **WHEN** la sesión es L6 en `ml-system-design`
- **THEN** el entrevistador exige además trade-offs a escala, disponibilidad, seguridad, validación online y alcance entre equipos

#### Scenario: Repregunta
- **WHEN** el candidato menciona "I'd use a two-tower model for retrieval"
- **THEN** el entrevistador repregunta sobre ese punto (negative sampling, cold start o serving) antes de cambiar de tema

### Requirement: Presupuesto de tiempo
Cada etapa SHALL tener un presupuesto de tiempo activo, escalado por `time_scale` y sin contar las pausas. Al 80 % el entrevistador SHALL avisar, al 90 % pasar a las preguntas del candidato y al 100 % cerrar la etapa.

#### Scenario: Tiempo agotado
- **WHEN** el tiempo activo escalado alcanza el presupuesto
- **THEN** el entrevistador cierra el tema en curso y termina la etapa

#### Scenario: Pausa
- **WHEN** el candidato pausa 10 minutos y luego reanuda
- **THEN** esos 10 minutos no cuentan en el presupuesto

### Requirement: Cultura basada en el memo vigente
La etapa `culture` SHALL evaluar 3–4 valores por sesión del memo vigente de Netflix (selflessness, judgment, candor, creativity, courage, inclusion, curiosity, resilience) y sus conceptos: keeper test, context not control, informed captain, farming for dissent y disagree then commit. Lo hará con preguntas conductuales que exigen casos concretos con impacto medible.

#### Scenario: Respuesta genérica
- **WHEN** el candidato responde con generalidades
- **THEN** el entrevistador pide un caso real: qué pasó, qué hizo, el resultado medible y qué haría distinto

### Requirement: Señales de cultura en todas las etapas
Todos los entrevistadores SHALL registrar las señales de cultura que observen. Cuando encaje con el tema de la etapa, SHOULD hacer una repregunta que las revele (p. ej. cómo defendería un trade-off ante un stakeholder).

#### Scenario: Señal observada en system design
- **WHEN** el candidato menciona espontáneamente que pidió opiniones contrarias antes de decidir
- **THEN** el entrevistador lo registra como señal del valor correspondiente

### Requirement: Mantener el idioma de la sesión
El entrevistador SHALL conducir la etapa en el idioma de la sesión aunque el candidato cambie de idioma. El cambio SHALL anotarse sin penalizar.

#### Scenario: Cambio de idioma del candidato
- **WHEN** el idioma es inglés y el candidato responde una vez en español
- **THEN** el entrevistador sigue en inglés y el cambio queda anotado
