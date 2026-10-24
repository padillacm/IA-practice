# Proposal

## Why

Preparar un loop de entrevistas de Machine Learning en Netflix exige practicar etapas muy distintas: screens, coding práctico, fundamentos, ML system design, experimentación, presentaciones, deep dive y cultura. Hoy no hay forma de ensayarlas con entrevistadores realistas, una evaluación independiente y un registro del progreso. El repo ya tiene el curso `recsys-course/` ("de cero a nivel Netflix") y el flujo multi-agente de `course-builder`. Un simulador en Claude Code, alineado con lo que se sabe públicamente del proceso (ver `research.md`), cierra el ciclo: estudiar, practicar, recibir feedback y volver a estudiar.

## What Changes

- **Nueva skill de Claude Code `/netflix-ml-interview`** que orquesta una sesión de entrevista simulada.
  - El candidato elige rol, nivel, idioma, dominio del equipo y **qué etapas simular**: el loop por defecto de su rol, una fase, una sola etapa o cualquier selección.
  - Roles: ML Engineer; Research / ML / Applied Scientist; Data Scientist (experimentation & analytics).
  - Niveles: L4–L6, con L5 por defecto.
  - Opcionalmente, el candidato puede aportar su CV o background.
- **Idioma**: todo en inglés por defecto (entrevista, scorecards y decisión final). `lang=es` lo pasa **todo a español**.
- **Catálogo de 14 etapas en tres fases**, basado en la investigación:
  - **Screens**: recruiter, HM y technical screen (con variantes por rol, incluida la revisión de un PR de producción).
  - **VO1** (general): presentation, coding, AI-assisted coding, ML fundamentals, ML system design, experimentation y culture ("Dream Team" con un director).
  - **VO2** (del equipo): ML depth, project deep dive, partnership y HM onsite.
  - Cada rol tiene su loop por defecto. El corte entre VO1 y VO2 está activo para MLE y es opcional en los demás roles.
- **17 subagentes**, todos sin Bash ni escritura:
  - Un entrevistador por etapa, con persona, estilo, banco de preguntas, repreguntas y presupuesto de tiempo, sin dar feedback durante la etapa.
  - Un evaluador que puntúa a ciegas, con citas verificadas y reglas pedagógicas explícitas.
  - Un debrief del hiring manager. Netflix no tiene hiring committee, así que el debrief simula la discusión del panel (pass / fail, buscando consenso) y la decisión del HM como "informed captain": Hire con nivel, No Hire, o "not a fit for this team, referred".
  - Un asistente "AI pair" para la ronda de AI-assisted coding.
- **Helper `sim.py` (stdlib)**: hace todo lo determinista. Eso incluye el guard de git, el estado de la sesión, el tiempo activo, la selección de preguntas, la ejecución de tests, la verificación de citas, la reconstrucción de entrevistadores y el progreso.
- **Sesiones solo en local**: se guardan en un directorio ignorado por git, y el sistema nunca las añade ni las commitea.
- **Base de conocimiento versionada** (`netflix-ml-interview/`) con catálogo, bancos, rúbricas, fuentes y un gold set de evaluación, separada de los prompts.

## Capabilities

### New Capabilities
- `interview-session`: configuración y orquestación de una sesión (rol, nivel, idioma, dominio, background, selección de etapas y fases), instancias de etapa, corte entre fases, comandos `::`, pausa, reanudación y modo degradado.
- `interview-stages`: catálogo de etapas y variantes, y comportamiento observable del entrevistador (persona, estilo, contrato de turno, ritmo, tiempo, coding ejecutable, AI-assisted coding, cultura).
- `interview-evaluation`: rúbricas versionadas, evaluación independiente con evidencia verificable, regla pedagógica de recomendación, pesos por rol, corte, debrief, plan de estudio y calidad del evaluador.
- `interview-history`: registro local de sesiones fuera de git, guardado incremental y progreso comparable.

### Modified Capabilities
<!-- Ninguna: el repo no tiene specs previos. -->

## Impact

- **Nuevos archivos**:
  - `.claude/skills/netflix-ml-interview/` (skill y protocolo de relevo);
  - `.claude/agents/netflix-*.md` (17 agentes);
  - `netflix-ml-interview/` (base de conocimiento, `sim.py` y validador);
  - `.gitignore` raíz con `netflix-ml-interview/sessions/`;
  - `.claude/settings.json` con un permiso para `sim.py`.
- **Dependencias**: ninguna en tiempo de ejecución, aparte de Claude Code y Python 3 (stdlib). El contenido de algunos problemas de coding usa numpy y pandas (`requirements.txt`). CI los instala y el validador los salta con un aviso si faltan.
- **CI**: un workflow en `.github/workflows/` que ejecuta el validador y los tests de `sim.py`. El comportamiento conversacional se verifica a mano, con el gold set y los smoke tests.
- **Contenido existente**: `recsys-course/` solo se lee, para enlazar el plan de estudio.
- **Limitaciones**:
  - Es una simulación basada en información pública, y buena parte de la evidencia viene de loops de SWE. Los loops reales varían por equipo, los descriptores L4 y L6 están extrapolados y no hay afiliación con Netflix.
  - En entornos efímeros (Claude Code en la web), las sesiones locales se pierden cuando se recicla el contenedor.
