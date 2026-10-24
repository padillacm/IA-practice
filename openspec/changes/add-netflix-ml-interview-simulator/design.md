# Design

## Context

- El repo es un espacio de aprendizaje: cursos en notebooks (`recsys-course/`, `langgraph/`, `langsmith/`…) y una skill multi-agente previa (`.claude/skills/course-builder/`) que usa `Agent` + `SendMessage` y checkpoints en git. Seguimos esas mismas convenciones: prompts en español y archivos de referencia junto a la skill.
- La plataforma es Claude Code, sin código de aplicación. Un subagente de Claude Code **no puede hablar directamente con el usuario**: recibe un prompt, trabaja y devuelve un informe. `SendMessage` reanuda un agente con su contexto intacto. Ese límite condiciona todo el diseño de la interacción.
- Las sesiones pueden correr en un contenedor efímero (Claude Code en la web), así que lo que no esté commiteado se pierde (ver spec `interview-history`).
- `recsys-course/` tiene 20 módulos (`00_intro` … `19_elite_playbook`) a los que enlaza el plan de estudio.

## Goals / Non-Goals

**Goals:**
- Que cada entrevistador sea un agente con contexto propio: su plan oculto de preguntas y su persona no contaminan al orquestador ni a otras etapas.
- Evaluación separada de la conducción: el evaluador solo ve la transcripción guardada.
- Contenido (catálogo, bancos de preguntas, rúbricas) separado de los prompts de los agentes, para mejorarlo sin tocar la orquestación.
- Coherencia comprobable de forma automática (catálogo ↔ agentes ↔ rúbricas ↔ enlaces al curso) con un script sin dependencias.

**Non-Goals:**
- Una app con el Agent SDK, interfaz web o voz.
- Replicar preguntas reales filtradas de Netflix. El banco se construye a partir de la descripción pública del proceso y de temas típicos de ML/recsys.
- Tests automáticos del comportamiento conversacional de los agentes con un candidato simulado (ver Open Questions).

## Decisions

### D1 · Patrón de relevo: orquestador ↔ entrevistador vía `SendMessage`
La skill (hilo principal) habla con el candidato. Para cada etapa lanza el agente entrevistador con `Agent` (en primer plano, con `name` = `entrevistador-<stage>-<session_id>`). Después, en cada turno, le reenvía la respuesta del candidato con `SendMessage` y muestra su réplica.
- **Por qué**: es la única forma, dentro de Claude Code, de tener un entrevistador con contexto aislado y persistente durante toda la etapa.
- **Alternativa A**: que el hilo principal adopte la persona (role-play en el mismo contexto). Es más rápido y barato, pero el orquestador vería el plan y la rúbrica y arrastraría el contexto entre etapas. Queda como **modo degradado** (D7).
- **Alternativa B**: un agente por pregunta. Rompe las repreguntas y la continuidad de la persona.

### D2 · Protocolo de turno con canal visible y canal meta
Cada réplica del entrevistador tiene dos bloques: `<say>` (lo único que ve el candidato) y `<meta>` en YAML (`question_id`, `hint_given`, `phase: intro|main|wrap_up|closed`, `notes_for_log`). El orquestador muestra `<say>` tal cual, sin parafrasear, y guarda `<meta>` en la transcripción.
- **Por qué**: permite registrar las pistas dadas (spec *Candidato atascado*), saber qué preguntas se usaron (spec *Evitar repetir preguntas*) y detectar el cierre de la etapa sin heurísticas sobre texto libre.
- **Alternativa**: texto libre con marcadores. Es frágil para detectar el cierre y la pista.

### D3 · Tiempo con marcas reales inyectadas por el orquestador
El orquestador toma `date -u +%s` al empezar la etapa y en cada turno, y antepone a cada mensaje relevado una cabecera `[t=23m/60m]`. Las reglas del aviso al 80 % y del cierre al 100 % están en el prompt del entrevistador. `/tiempo`, `/pausa` y `/terminar-etapa` los intercepta el orquestador y no llegan al entrevistador, salvo `/terminar-etapa`, que se traduce a `[orquestador: cierra la etapa]`.

### D4 · Agentes finos por etapa + paquetes de contenido
- `.claude/agents/netflix-<stage>.md` (9 archivos): frontmatter (`name`, `description`, `tools`, `model`) y un prompt corto con la persona, las reglas de realismo y el protocolo D2, con instrucciones de leer su paquete de etapa al arrancar. Solo `netflix-coding` tiene `Bash` (para ejecutar tests); el resto, solo `Read`, `Glob` y `Grep`.
- `.claude/agents/netflix-evaluator.md` (genérico; recibe la ruta a la rúbrica) y `.claude/agents/netflix-hiring-committee.md`.
- **Por qué uno por etapa y no uno genérico**: permisos de herramientas distintos (coding), visibilidad en `/agents` y personas diferenciadas. El contenido pesado vive fuera, así que la duplicación es mínima.

### D5 · Base de conocimiento en `netflix-ml-interview/`
```
netflix-ml-interview/
  README.md                     # qué es, cómo se usa, aviso de no afiliación
  catalog.yaml                  # orden canónico, duración, roles, variantes, competencias, agente
  study-map.yaml                # tema/competencia -> ruta de recsys-course/
  stages/<stage>/
    brief.md                    # objetivo, estructura de la etapa, persona, qué observa
    questions.md                # banco con id, rol, nivel, repreguntas esperadas
    rubric.md                   # 3–6 competencias × 4 puntos × L4/L5/L6
  stages/coding/problems/<id>/  # problem.md, starter.py, tests.py, reference.py
  scripts/check_simulator.py    # validación de coherencia (stdlib)
  sessions/
    PROGRESS.md
    <YYYY-MM-DD>-<id>/
      session.yaml              # config, estado por etapa, timestamps, question_ids usados
      <NN>-<stage>.transcript.md
      <stage>.scorecard.md
      committee.md
      code/                     # espacio de trabajo de coding
```
- Duraciones objetivo (min): recruiter-screen 30, hiring-manager 45, coding 60, ml-fundamentals 45, ml-system-design 60, ml-depth 45, experimentation 45, project-deep-dive 45, culture 45.
- Aplicabilidad por rol en `catalog.yaml`. La variante de `coding` para Applied/Data Scientist es SQL/pandas + estadística aplicada; para MLE/RS es algoritmos y estructuras de datos + manipulación de datos en Python. Research Scientist incluye `project-deep-dive` como presentación de investigación.
- **Por qué YAML + markdown**: lo pueden leer las personas y los agentes, da diffs limpios en git y no requiere dependencias.

### D6 · Evaluación y comité
Al cerrar una etapa, el orquestador lanza `netflix-evaluator` en segundo plano con: la ruta de la transcripción, `session.yaml` y `rubric.md`. Mientras tanto ofrece la transición. Si el feedback es inmediato (por defecto), espera la notificación del evaluador antes de mostrar el scorecard. `netflix-hiring-committee` recibe solo los scorecards y la configuración (no las transcripciones) para imitar a un comité real que lee el feedback escrito; puede abrir una transcripción concreta si un scorecard no tiene evidencia suficiente. Idiomas: la entrevista en el idioma de la sesión (por defecto **inglés**, por realismo), y scorecards y veredicto siempre en **español**.

### D7 · Modo degradado sin `SendMessage`
Si `SendMessage` no está disponible (la skill lo carga con `ToolSearch`), el orquestador avisa y conduce la etapa en el hilo principal con la persona del entrevistador. La evaluación sigue siendo un agente separado, así que la independencia de la evaluación (spec) se mantiene.

### D8 · Persistencia y commit
El orquestador añade cada turno a la transcripción justo después de recibirlo (spec *Guardado incremental*) y actualiza `session.yaml` en cada transición. Al pausar o terminar ofrece `git add netflix-ml-interview/sessions/<id> netflix-ml-interview/sessions/PROGRESS.md && git commit` y solo lo ejecuta tras la confirmación del candidato. `PROGRESS.md` se regenera desde todos los `session.yaml` y scorecards (fuente única de verdad: los directorios de sesión).

## Risks / Trade-offs

- [Latencia y coste: cada turno es una llamada a un subagente] → Los agentes de etapa usan contexto mínimo (el paquete de etapa se carga una vez) y el `model` es configurable en el frontmatter. El modo degradado D7 queda disponible si el usuario prefiere velocidad.
- [El entrevistador filtra la rúbrica o da feedback en vivo] → Reglas explícitas en el prompt, rúbrica fuera de su lectura obligatoria (lee `brief.md` y `questions.md`; la rúbrica solo la lee el evaluador) y una prueba manual de humo por etapa en tasks.
- [El orquestador parafrasea o "ayuda" al candidato] → La skill exige mostrar `<say>` sin cambios y prohíbe comentar las respuestas durante la etapa.
- [Proceso de Netflix inexacto o desactualizado] → Contenido basado en fuentes públicas citadas en cada `brief.md`, aviso en el README y catálogo editable.
- [Sesiones con datos personales commiteadas en un repo público] → El commit siempre se pide de forma explícita. El README explica cómo añadir `sessions/` a `.gitignore` si se prefiere.
- [Rúbricas poco calibradas → puntuaciones infladas] → El evaluador debe citar evidencia por competencia y marcar "sin evidencia". El script valida que la rúbrica esté completa.

## Migration Plan

No aplica: es un añadido nuevo, sin datos ni comportamiento previos. Para deshacerlo basta con borrar `.claude/skills/netflix-ml-interview/`, `.claude/agents/netflix-*.md` y `netflix-ml-interview/`.

## Open Questions

- ¿Añadir más adelante un agente "candidato simulado" para smoke tests automáticos de cada etapa? No cambia specs ni el diseño base; sería un change aparte.
- ¿Qué `model` por defecto usar para los entrevistadores frente al evaluador? Se puede ajustar en el frontmatter tras las primeras sesiones, sin cambiar el diseño.
