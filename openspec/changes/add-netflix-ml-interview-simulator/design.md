# Design

## Context

- El repo es un espacio de aprendizaje: cursos en notebooks (`recsys-course/`, `langgraph/`, `langsmith/`…) y una skill multi-agente previa (`.claude/skills/course-builder/`) que usa `Agent` + `SendMessage`. Seguimos esas convenciones: archivos de referencia junto a la skill y documentación del repo en español.
- La plataforma es Claude Code, sin código de aplicación. Un subagente **no puede hablar directamente con el usuario**: recibe un prompt, trabaja y devuelve un informe. `SendMessage` reanuda un agente con su contexto intacto. Ese límite condiciona el diseño de la interacción.
- El formato de cada etapa sale de `research.md`. Lo más relevante para el diseño: los loops varían por equipo, no hay hiring committee (debrief + decisión del HM), la cultura se evalúa en todas las rondas, `presentation` tiene material previo y system design es la ronda con más peso para MLE.
- Las sesiones deben quedarse en local y fuera de git. En Claude Code en la web, el contenedor es efímero (variable `CLAUDE_CODE_REMOTE=true`).
- `recsys-course/` tiene 20 módulos (`00_intro` … `19_elite_playbook`) a los que enlaza el plan de estudio.

## Goals / Non-Goals

**Goals:**
- Que cada entrevistador sea un agente con contexto propio: su plan oculto de preguntas y su persona no contaminan al orquestador ni a otras etapas.
- Evaluación separada de la conducción: el evaluador solo ve la transcripción guardada.
- Contenido (catálogo, bancos, rúbricas, fuentes) separado de los prompts de los agentes, para mejorarlo sin tocar la orquestación.
- Coherencia comprobable de forma automática con un script sin dependencias: catálogo ↔ agentes ↔ rúbricas ↔ enlaces al curso ↔ `.gitignore`.

**Non-Goals:**
- Una app con el Agent SDK, interfaz web o voz.
- Replicar preguntas reales filtradas de Netflix. Los bancos se basan en temas reportados y prácticas documentadas.
- Sincronizar el historial entre máquinas o contenedores (las sesiones son locales por decisión del usuario).
- Tests automáticos del comportamiento conversacional con un candidato simulado (ver Open Questions).

## Decisions

### D1 · Patrón de relevo: orquestador ↔ entrevistador vía `SendMessage`
La skill (hilo principal) habla con el candidato. Para cada etapa lanza el agente entrevistador con `Agent` (en primer plano, `name` = `interviewer-<stage>-<session_id>`). Después, en cada turno, le reenvía la respuesta del candidato con `SendMessage` y muestra su réplica.
- **Por qué**: es la única forma, dentro de Claude Code, de tener un entrevistador con contexto aislado y persistente durante toda la etapa.
- **Alternativa A**: que el hilo principal adopte la persona (role-play). Es más barato, pero el orquestador vería el plan y la rúbrica y arrastraría el contexto entre etapas. Queda como modo degradado (D9).
- **Alternativa B**: un agente por pregunta. Rompe las repreguntas y la continuidad de la persona.
- **`presentation`**: el panel de dos personas lo simula un único agente que alterna dos personas declaradas en el brief (p. ej. "Priya, Staff RS" y "Marco, Senior DS"), en lugar de dos agentes coordinados, que duplicarían el coste sin ganar realismo perceptible.

### D2 · Protocolo de turno con canal visible y canal meta
Cada réplica del entrevistador tiene dos bloques: `<say>` (lo único que ve el candidato) y `<meta>` en YAML (`question_id`, `hint_given`, `culture_probe`, `phase: intro|main|candidate_questions|closed`, `notes_for_log`). El orquestador muestra `<say>` sin cambios y guarda `<meta>` en la transcripción.
- **Por qué**: permite registrar las pistas, las preguntas usadas (para no repetirlas) y las preguntas de cultura (spec *Señales de cultura en todas las etapas*), y detectar el cierre sin heurísticas sobre texto libre.

### D3 · Tiempo con marcas reales inyectadas por el orquestador
El orquestador toma `date -u +%s` al empezar la etapa y en cada turno, y antepone a cada mensaje relevado `[t=23m/60m]`. Las reglas del aviso al 80 % y del cierre al 100 % están en el prompt del entrevistador. El orquestador intercepta `/time` y `/pause`; `/end-stage` se traduce a `[orchestrator: close the stage]`. En `technical-screen` de MLE, el brief marca el cambio de bloque (proyecto previo → ML coding) hacia el minuto 20.

### D4 · Catálogo y loops por rol (de `research.md`)

| Etapa | Fase | Min | MLE | RS | Applied/DS | Persona |
|---|---|---|---|---|---|---|
| recruiter-screen | screen | 30 | ● | ● | ● | Recruiter |
| hiring-manager | screen | 45 | ● | ● | ● | Hiring manager del equipo |
| technical-screen | screen | 60 | ● proyecto + ML coding | ● stats/ML + coding | ● SQL + caso | Senior MLE / RS / DS |
| presentation | loop | 60 | ○ | ● research talk | ● take-home readout | Panel de 2 |
| coding | loop | 60 | ● Python práctico/algorítmico | ● ML coding | ● SQL/pandas | Senior MLE / DS |
| ml-fundamentals | loop | 45 | ○ | ● | ● caso de modelado | RS / Senior DS |
| ml-system-design | loop | 60 | ● (peso máximo) | ○ | ○ | Staff MLE |
| ml-depth | loop | 45 | ● | ● | ○ | Experto del dominio del equipo |
| experimentation | loop | 45 | ○ | ○ | ● (decisiva) | Senior DS (experimentación) |
| project-deep-dive | loop | 45 | ● | ○ | ○ | Senior MLE |
| culture | loop | 45 | ● | ● | ● | Director (de la org que contrata o de una socia) |

● = loop por defecto, ○ = opcional. `ml-depth` pide al configurar el dominio del equipo (recsys, causal inference, RL/bandits, CV/NLP/LLM, ads); por defecto, recsys.

### D5 · Agentes finos por etapa + paquetes de contenido
- `.claude/agents/netflix-<stage>.md` (11 archivos): frontmatter (`name`, `description`, `tools`, `model`) y un prompt corto con la persona, las reglas de realismo, el protocolo D2, el sondeo de cultura y la regla de idioma. Al arrancar lee `brief.md` y `questions.md` de su etapa, **nunca `rubric.md`**. Solo `netflix-coding` y `netflix-technical-screen` tienen `Bash` (para ejecutar tests); el resto, `Read`, `Glob` y `Grep`.
- `.claude/agents/netflix-evaluator.md` (genérico; recibe la ruta a la rúbrica) y `.claude/agents/netflix-hm-debrief.md`.
- **Por qué uno por etapa**: permisos de herramientas distintos, visibilidad en `/agents` y personas diferenciadas. El contenido pesado vive fuera, así que la duplicación es mínima.

### D6 · Base de conocimiento en `netflix-ml-interview/`
```
netflix-ml-interview/
  README.md                     # uso, comandos, aviso de no afiliación y de variabilidad
  catalog.yaml                  # D4: fase, duración, variantes, loops por rol, competencias, persona, agente
  study-map.yaml                # competencia/tema -> ruta de recsys-course/
  sources.md                    # fuentes de research.md con nivel de confianza
  stages/<stage>/
    brief.md                    # objetivo, estructura temporal, persona, variantes, fuentes
    questions.md                # banco: id, rol, nivel, variante, repreguntas, sondeo de cultura
    rubric.md                   # 3–6 competencias (una de cultura) × 4 puntos × L4/L5/L6
  stages/coding/problems/<id>/  # problem.md, starter.py, tests.py, reference.py (también los usa technical-screen)
  stages/presentation/takehomes/<id>/  # prompt.md + generate_data.py (dataset sintético con semilla)
  templates/                    # scorecard.md, debrief.md, session.yaml
  scripts/check_simulator.py    # validación (stdlib)
  sessions/                     # IGNORADO por git (ver D8)
```
- **Idioma del contenido**: la base de conocimiento y los prompts de los agentes se escriben en **inglés** (el idioma por defecto). En `lang=es`, los agentes conducen la entrevista y redactan los informes en español a partir de ese contenido, sin traducir los términos técnicos estándar. Así hay una única fuente de contenido y no dos que mantener sincronizadas. El README del directorio va en español, siguiendo la convención del repo.

### D7 · Evaluación y debrief
- Al cerrar una etapa, el orquestador lanza `netflix-evaluator` en segundo plano con la ruta de la transcripción, `session.yaml` y `rubric.md`. El scorecard incluye la recomendación pass / no-pass del entrevistador.
- `netflix-hm-debrief` recibe solo los scorecards y la configuración, igual que un HM que lee el feedback escrito del panel. Simula un debrief corto (cada entrevistador resume su recomendación), aplica la regla de consenso alto (un "Strong No" en una competencia central suele bloquear) y decide como informed captain, teniendo en cuenta las necesidades del equipo. Puede abrir una transcripción concreta si falta evidencia.
- La escala de 4 puntos es una herramienta pedagógica; el README explica que Netflix no usa una escala común a toda la empresa.

### D8 · Sesiones solo locales
- Ruta: `netflix-ml-interview/sessions/`, con la entrada `netflix-ml-interview/sessions/` en el `.gitignore` raíz.
- Antes de crear una sesión, la skill ejecuta `git check-ignore -q netflix-ml-interview/sessions/` y, si falla, se niega a escribir (spec *Ignore ausente*). La skill no contiene ninguna instrucción `git add`/`commit`/`push` sobre esa ruta, y `check_simulator.py` verifica tanto la entrada del `.gitignore` como esa ausencia en el texto de la skill.
- Si `CLAUDE_CODE_REMOTE=true`, el resumen de configuración incluye el aviso de entorno efímero.
- Estructura de cada sesión: `<YYYY-MM-DD>-<id>/session.yaml`, `<NN>-<stage>.transcript.md`, `<stage>.scorecard.md`, `debrief.md`, `code/` y `takehome/`. `PROGRESS.md` se regenera desde todos los `session.yaml` y scorecards.

### D9 · Modo degradado sin `SendMessage`
Si `SendMessage` no está disponible (la skill lo carga con `ToolSearch`), el orquestador avisa y conduce la etapa en el hilo principal con la persona del entrevistador. La evaluación sigue siendo un agente separado.

## Risks / Trade-offs

- [Latencia y coste: cada turno es una llamada a un subagente] → Contexto mínimo por agente (el paquete se carga una vez) y `model` configurable en el frontmatter. El modo D9 queda disponible si el usuario prefiere velocidad.
- [El entrevistador filtra la rúbrica o da feedback en vivo] → El entrevistador no lee la rúbrica, las reglas son explícitas en el prompt y hay un smoke test por etapa.
- [El orquestador parafrasea o "ayuda" al candidato] → La skill exige mostrar `<say>` sin cambios y prohíbe comentar respuestas durante la etapa.
- [Proceso de Netflix inexacto o cambiante; las fuentes son mayoritariamente de terceros] → Confianza explícita por hallazgo en `sources.md`, aviso de variabilidad en cada sesión y catálogo editable. Revisar `research.md` cuando Netflix publique un memo o un formato nuevo.
- [Pérdida del historial en contenedores efímeros] → Es una consecuencia aceptada de la decisión de no versionar las sesiones. Se avisa al iniciar; en uso local con el CLI, el historial persiste en disco.
- [Rúbricas poco calibradas → puntuaciones infladas] → Cita de evidencia obligatoria por competencia, "no evidence" cuando falta y validación de que la rúbrica está completa.

## Migration Plan

No aplica: es un añadido nuevo. Para deshacerlo basta con borrar `.claude/skills/netflix-ml-interview/`, `.claude/agents/netflix-*.md`, `netflix-ml-interview/` y la línea del `.gitignore`.

## Open Questions

- ¿Añadir más adelante un agente "candidato simulado" para smoke tests automáticos de cada etapa? Sería un change aparte.
- ¿Qué `model` por defecto usar para los entrevistadores frente al evaluador? Se puede ajustar en el frontmatter tras las primeras sesiones.
