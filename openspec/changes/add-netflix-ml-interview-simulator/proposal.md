# Proposal

## Why

Preparar un loop de entrevistas de Machine Learning en Netflix exige practicar etapas muy distintas: screens, coding práctico, fundamentos, ML system design, experimentación, presentaciones, deep dive y cultura. Hoy no hay forma de ensayarlas con entrevistadores realistas, una evaluación independiente y un registro del progreso. El repo ya tiene el curso `recsys-course/` ("de cero a nivel Netflix") y el flujo multi-agente de `course-builder`. Un simulador en Claude Code, alineado con lo que se sabe públicamente del proceso (ver `research.md`), cierra el ciclo: estudiar, practicar, recibir feedback y volver a estudiar.

## What Changes

- Nueva skill de Claude Code `/netflix-ml-interview` que orquesta una sesión de entrevista simulada. El candidato elige el rol (ML Engineer, Research Scientist, Applied/Data Scientist), el nivel (L4–L6), el idioma y **qué etapas simular**: el loop por defecto de su rol, una sola etapa o cualquier selección.
- **Idioma: todo en inglés por defecto** (entrevista, scorecards y decisión final). Una opción configura **todo en español**.
- Catálogo de **11 etapas** basado en la investigación: `recruiter-screen`, `hiring-manager`, `technical-screen`, `presentation` (research talk o take-home readout), `coding`, `ml-fundamentals`, `ml-system-design`, `ml-depth`, `experimentation`, `project-deep-dive` y `culture`, con un loop por defecto para cada rol.
- Un subagente entrevistador por etapa (en `.claude/agents/`) con persona, banco de preguntas, repreguntas y presupuesto de tiempo propios, sin feedback durante la etapa. Cada entrevistador evalúa también señales de cultura, porque en Netflix la cultura se evalúa en todas las rondas.
- Un subagente evaluador que puntúa cada transcripción a ciegas contra una rúbrica por competencias y emite la recomendación pass / no-pass del entrevistador.
- En lugar de un hiring committee (Netflix no lo tiene), un subagente **debrief del hiring manager** que simula el debrief del panel y la decisión del hiring manager como "informed captain": Hire / No Hire y nivel, con un plan de estudio que enlaza módulos de `recsys-course/`.
- **Sesiones solo en local**: transcripciones, scorecards y decisiones se guardan en un directorio ignorado por git y el sistema nunca las añade ni las commitea.
- Base de conocimiento versionada (`netflix-ml-interview/`) con el catálogo, los bancos de preguntas, las rúbricas y las fuentes, separada de los prompts de los agentes.

## Capabilities

### New Capabilities
- `interview-session`: configuración y orquestación de una sesión (rol, nivel, idioma, selección de etapas), loops por rol, orden y transición entre etapas, pausa y reanudación.
- `interview-stages`: catálogo de etapas y comportamiento observable del entrevistador en cada una (persona, preguntas, repreguntas, tiempo, materiales previos, cierre, sin feedback en vivo).
- `interview-evaluation`: rúbricas por competencia, scorecard por etapa evaluado de forma independiente, recomendación pass / no-pass y debrief con decisión del hiring manager y plan de estudio.
- `interview-history`: registro local de sesiones fuera de git y resumen de progreso del candidato.

### Modified Capabilities
<!-- Ninguna: el repo no tiene specs previos. -->

## Impact

- **Nuevos archivos**: `.claude/skills/netflix-ml-interview/` (skill orquestadora), `.claude/agents/netflix-*.md` (entrevistadores, evaluador y debrief), `netflix-ml-interview/` (base de conocimiento) y una entrada en `.gitignore` para `netflix-ml-interview/sessions/`.
- **Dependencias**: ninguna en tiempo de ejecución; solo Claude Code (skills, subagentes y SendMessage). Un script en Python (stdlib) valida la coherencia entre el catálogo, los agentes, las rúbricas y el `.gitignore`.
- **CI**: un job ligero en `.github/workflows/` que ejecuta ese script.
- **Contenido existente**: solo lectura de `recsys-course/` para enlazar el plan de estudio.
- **Limitaciones**: es una simulación basada en información pública; los loops reales varían por equipo y no hay afiliación con Netflix. En entornos efímeros (Claude Code en la web), las sesiones locales se pierden cuando se recicla el contenedor.
