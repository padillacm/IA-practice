# Proposal

## Why

Preparar un loop de entrevistas de Machine Learning en Netflix exige practicar etapas muy distintas: screens, coding, fundamentos, ML system design, experimentación, deep dive y cultura. Hoy no hay forma de ensayarlas con un entrevistador realista, una evaluación independiente y un registro del progreso. El repo ya tiene el curso `recsys-course/` ("de cero a nivel Netflix") y el flujo multi-agente de `course-builder`. Un simulador en Claude Code cierra el ciclo: estudiar, practicar la entrevista, recibir el feedback y volver a estudiar.

## What Changes

- Nueva skill de Claude Code `/netflix-ml-interview` que orquesta una sesión de entrevista simulada. El candidato elige el rol (ML Engineer, Research Scientist, Applied/Data Scientist), el nivel (L4–L6), el idioma y **qué etapas simular**: el loop completo, una sola etapa o una selección.
- Un catálogo de etapas que modela el proceso de Netflix para roles de ML: recruiter screen, hiring manager, coding, ML fundamentals, ML system design, ML depth (dominio), experimentación y A/B testing, project deep dive y culture (memo de cultura de Netflix).
- Un subagente entrevistador por etapa (en `.claude/agents/`) con persona, banco de preguntas, repreguntas y presupuesto de tiempo propios. Cada uno funciona sin pistas ni feedback durante la etapa, igual que una entrevista real.
- Un subagente evaluador que puntúa la transcripción de cada etapa a ciegas contra una rúbrica por competencias y produce un scorecard. Al final, un subagente "hiring committee" consolida los scorecards en un veredicto (hire / no hire y nivel), con fortalezas, brechas y un plan de estudio que enlaza módulos de `recsys-course/`.
- Persistencia de cada sesión (configuración, transcripciones, scorecards y veredicto) en markdown/YAML dentro del repo, más un resumen de progreso entre sesiones.
- Base de conocimiento versionada (`netflix-ml-interview/`) con la descripción de cada etapa, los bancos de preguntas y las rúbricas, separada de los prompts de los agentes.

## Capabilities

### New Capabilities
- `interview-session`: configuración y orquestación de una sesión (rol, nivel, idioma, selección de etapas), orden y transición entre etapas, pausa y reanudación.
- `interview-stages`: catálogo de etapas y comportamiento observable del entrevistador en cada una (persona, preguntas, repreguntas, tiempo, cierre, sin feedback en vivo).
- `interview-evaluation`: rúbricas por competencia, scorecard por etapa evaluado de forma independiente y veredicto del hiring committee con plan de estudio.
- `interview-history`: registro persistente de sesiones y resumen de progreso del candidato a lo largo del tiempo.

### Modified Capabilities
<!-- Ninguna: el repo no tiene specs previos. -->

## Impact

- **Nuevos archivos**: `.claude/skills/netflix-ml-interview/` (skill orquestadora), `.claude/agents/netflix-*.md` (entrevistadores, evaluador y comité), `netflix-ml-interview/` (base de conocimiento y `sessions/`).
- **Dependencias**: ninguna en tiempo de ejecución; solo Claude Code (skills, subagentes y SendMessage). Un script de validación en Python (stdlib) comprueba la coherencia entre el catálogo, los agentes y las rúbricas.
- **CI**: opcionalmente, un job ligero en `.github/workflows/` que ejecute ese script.
- **Contenido existente**: solo lectura de `recsys-course/` para enlazar el plan de estudio; no se modifica.
- **Aviso**: es una simulación basada en información pública; las etapas reales varían por equipo y no hay afiliación con Netflix.
