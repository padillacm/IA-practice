# Design

## Context

- El repo es un espacio de aprendizaje: cursos en notebooks (`recsys-course/`, `langgraph/`, `langsmith/`…) y una skill multi-agente previa (`.claude/skills/course-builder/`) que usa `Agent` + `SendMessage`. No hay `.gitignore` raíz ni `.claude/settings.json` de proyecto.
- La plataforma es Claude Code, sin código de aplicación. Un subagente **no puede hablar con el usuario ni esperar su respuesta**: recibe un prompt, trabaja y devuelve un mensaje final.
  - `SendMessage` a un agente con nombre lo reanuda desde su transcripción, pero **la respuesta llega después como notificación**, no como resultado de la herramienta. Solo la primera llamada a `Agent` en primer plano es síncrona.
  - Los mensajes que empiezan por `/` los interpreta la CLI como slash commands, y `!` activa el modo bash.
- El formato de cada etapa sale de `research.md`. Lo más relevante para el diseño:
  - los loops varían por equipo;
  - en loops de SWE/MLE se reporta un onsite dividido en VO1 y VO2 con un corte (confianza Media para otros roles);
  - no hay hiring committee: la decisión es pass / fail en una discusión en vivo y la toma el HM;
  - la cultura se evalúa en todas las rondas;
  - existen rondas de AI-assisted coding y de partnership.
- Las sesiones son locales y están fuera de git. En Claude Code en la web el contenedor es efímero (`CLAUDE_CODE_REMOTE=true`) y un Stop hook pide hacer commit de los archivos sin rastrear: la protección real es el `.gitignore`.
- El usuario también ejecuta Claude Code en Windows, así que no se puede depender de `date`, `python3` ni de sintaxis de bash.
- `recsys-course/` tiene 20 módulos (`00_intro` … `19_elite_playbook`); no cubre coding, SQL ni cultura.

## Goals / Non-Goals

**Goals:**
- Cada entrevistador es un agente con contexto propio, y su evaluación la hace otro agente distinto que solo ve hechos.
- Todo el estado y todo el cálculo determinista viven en un helper stdlib, `sim.py`, y en `session.yaml`, no en la memoria de la conversación ni en la aritmética del modelo. Eso incluye el tiempo, la selección de preguntas, los tests, la verificación de citas y el guard de git.
- El contenido (catálogo, bancos, rúbricas, fuentes) está separado de los prompts, con formatos congelados (D10) y validados automáticamente.
- Funciona igual en Linux, macOS y Windows.

**Non-Goals:**
- Una app con el Agent SDK, interfaz web o voz.
- Replicar preguntas filtradas de Netflix.
- Sincronizar el historial entre máquinas: las sesiones son locales por decisión del usuario.
- Medir la fiabilidad del juez en CI. Se mide con un gold set ejecutado a mano (D7); CI solo valida estructura y contenido.
- Ocultar técnicamente el contenido al candidato, porque el repo es suyo. Se usa una regla de honor documentada (D5).

## Decisions

### D1 · Relevo asíncrono orquestador ↔ entrevistador
La skill (hilo principal) habla con el candidato. Cada etapa es una **instancia** con id `NN-<stage>@<variant>` (p. ej. `04-technical-screen@stats`) y un agente con nombre `iv-<instance>-<session_id>-<attempt>`. La máquina de estados está escrita, numerada, en `.claude/skills/netflix-ml-interview/references/relay-protocol.md`:

1. **Apertura**: `Agent` en primer plano con `subagent_type: netflix-<stage>` y el *launch packet* (D10). La respuesta es síncrona: se muestra `<say>` y se registra.
2. **Turno del candidato**: `sim.py turn` registra el texto del candidato y devuelve la cabecera de tiempo y los flags (D3). La skill hace `SendMessage` al entrevistador con `<orchestrator>…</orchestrator>` + `<candidate>…</candidate>` y **termina su turno sin texto para el candidato**.
3. **Notificación**: al llegar la respuesta, la skill comprueba que viene del entrevistador actual. Muestra `<say>` exactamente como llega, registra `<meta>` con `sim.py log` y se detiene. Las notificaciones de otros agentes (p. ej. el evaluador en segundo plano) nunca se muestran dentro de la entrevista.
4. **Mensajes adelantados**: si el candidato escribe antes de que llegue la respuesta, su mensaje se retiene y se envía después.

- **Saneado**: el texto del candidato va dentro de `<candidate>`, y se eliminan los marcadores `<orchestrator>` o `[orchestrator:` que contenga, para que no pueda falsificar directivas.
- **Por qué este patrón**: es la única forma, dentro de Claude Code, de tener un entrevistador con contexto aislado y persistente.
- **Alternativas descartadas**: el role-play en el hilo principal (queda como modo degradado, D9) y un agente por pregunta (rompe las repreguntas).
- **Panel**: `presentation` simula el panel con un único agente que alterna las dos personas declaradas en su brief.

### D2 · Contrato de turno `<say>` / `<meta>`
Cada prompt de entrevistador incluye literalmente: *"Each turn you MUST end with a final message containing exactly one `<say>…</say>` followed by one `<meta>…</meta>` and nothing after. Never write or guess the candidate's reply. Never call tools after writing `<say>`. Read files only on your first turn; later turns are pure conversation. Reply as your final message, never via SendMessage."*

- `<meta>` es YAML con estos campos **factuales**:
  - `question_id`
  - `phase: intro|main|candidate_questions|closed`
  - `hint {id, level: nudge|substantive, competency}`
  - `culture_probe {value}`
  - `time_warning_given`
  - `uncovered_signal_points[]`
  - `lang_switch`
  - `flaws_triggered[]` y `flaws_detected[]` (solo en ai-assisted-coding)
- Hay un único campo privado, `notes_private`, que `sim.py` elimina de la copia que recibe el evaluador. Fuera de `notes_private` está prohibido el lenguaje valorativo.
- **Reformateo**: si falta `<say>` o `<meta>`, se pide reformatear una sola vez. Si vuelve a fallar, se muestra el texto en bruto y se marca en la transcripción.

### D3 · Tiempo calculado por `sim.py`
- `session.yaml` guarda segmentos de tiempo activo por instancia. `::pause` cierra el segmento abierto y reanudar abre uno nuevo.
- `sim.py turn` calcula `t = activo / time_scale` y emite `[t=23m/60m]` junto con estos flags literales, que el entrevistador obedece sin hacer cálculos:
  - `[time:80% — give the time warning now]`
  - `[time:90% — move to candidate questions]`
  - `[time:100% — close the stage now]`
- `time_scale` vale 1.5 por defecto, porque escribir es más lento que hablar (`time_scale=1.0` lo desactiva). Las duraciones del catálogo son supuestos documentados en `sources.md`.

### D4 · Catálogo, fases y loops por rol (de `research.md`)

| Etapa | Min | Variantes (por defecto por rol) | Persona |
|---|---|---|---|
| recruiter-screen | 30 | — | Recruiter |
| hm-screen | 30 | — | HM (cordial, vende Netflix) |
| technical-screen | 60 | `ml-coding` (MLE), `ml-framing-coding` (RS), `sql` + `stats` (DS); opcionales `fundamentals-pr-review`, `intern-project-coding`, `oa` | Senior MLE / RS / DS |
| presentation | 45–60 | `research-talk` 45' (RS), `take-home` 60' (DS) | Panel de 2 |
| coding | 60 | `practical` (MLE), `ml-coding` (RS), `sql-pandas` (DS); opcional `lc-style` | Senior MLE / DS |
| ai-assisted-coding | 60 | — | Senior engineer |
| ml-fundamentals | 45 | `breadth` (RS); opcional `modeling-case` (DS, sin evidencia directa) | RS / Senior DS |
| ml-system-design | 60 | `design` (MLE), `problem-framing` (RS) | Staff MLE o director |
| experimentation | 45 | `design-case` + `analysis-case` (DS); `design-case` opcional para MLE y RS | Senior DS |
| culture | 45 | — | Director ("Dream Team") |
| ml-depth | 45 | — (la orienta el dominio) | Experto del dominio |
| project-deep-dive | 45 | — | Senior MLE ("reverse system design") |
| partnership | 45 | — | Manager o director de un equipo socio |
| hm-onsite | 45 | — | HM (exigente, encaje con el equipo) |

**Loops por defecto.** La fase pertenece a la entrada del loop, no a la etapa:

| Rol | screen | VO1 | VO2 | Corte | Dominio por defecto |
|---|---|---|---|---|---|
| `mle` ML Engineer | recruiter-screen, hm-screen, technical-screen@ml-coding | coding@practical, ml-system-design@design, culture | ml-depth, project-deep-dive, partnership, hm-onsite | sí | recsys |
| `rs` Research / ML / Applied Scientist | recruiter-screen, hm-screen, technical-screen@ml-framing-coding | presentation@research-talk, ml-system-design@problem-framing, ml-fundamentals@breadth, coding@ml-coding, culture | ml-depth, partnership, hm-onsite | no (opcional) | recsys |
| `ds` Data Scientist (experimentation & analytics) | recruiter-screen, hm-screen, technical-screen@sql, technical-screen@stats | presentation@take-home, experimentation@design-case, experimentation@analysis-case, coding@sql-pandas, culture | partnership, hm-onsite | no (opcional) | experimentation |

- **Orden canónico**: primero la fase (screen → VO1 → VO2) y, dentro de cada fase, el orden del catálogo. Una etapa elegida fuera de un loop usa `default_phase` y `variant_by_role`.
- **Dominios**: recsys, experimentation, causal-inference, rl-bandits, cv, nlp-llm, ads y ml-platform. El dominio orienta `ml-depth`, `ml-system-design` y `hm-onsite`.
- **Pesos por rol**, en el catálogo como `weight: high|normal|low`:
  - MLE: `ml-system-design`, `culture` y `ml-depth` en `high`; `coding` en `low`.
  - RS: `presentation`, `problem-framing`, `ml-depth` y `culture` en `high`.
  - DS: las dos instancias de `experimentation`, `stats` y `culture` en `high`.

### D5 · Agentes (17) y regla de honor

| Agente | tools | model |
|---|---|---|
| `netflix-<stage>` ×14 | Read, Glob, Grep | sonnet; `ml-system-design` y `hm-onsite`: opus |
| `netflix-evaluator` | Read, Glob, Grep | opus |
| `netflix-hm-debrief` (modos `cut` y `final`) | Read, Glob, Grep | opus |
| `netflix-ai-pair` | Read, Glob, Grep | sonnet |

- **Ningún agente tiene Bash ni Write.**
  - Los tests los ejecuta el hilo principal con `sim.py run-tests`, a la vista del candidato, y el resultado se inyecta como `[tests: 7/8 passed; failing: test_ties]`.
  - Los agentes devuelven markdown y es el hilo principal quien escribe los archivos.
- **Carga de agentes**: el `name` del frontmatter coincide con el nombre del archivo. Los agentes se cargan al iniciar Claude Code, así que después de crearlos hay que reiniciar o comprobar `/agents`.
- **ai-pair**:
  - Es un agente persistente por instancia (`ai-<instance>-<sid>`) que el candidato usa con `::ai <prompt>`.
  - Devuelve una explicación y un diff unificado, sin editar nada. `::apply` aplica el diff con `sim.py apply`.
  - Cada repo trae un `flaws.yaml` con 0–2 errores (a veces ninguno).
  - La skill pasa al entrevistador, como `<orchestrator private>`, un resumen del intercambio y los `flaws_triggered`. El entrevistador "ve la pantalla" del candidato y no debe revelarlos.
- **Regla de honor** (README): durante la práctica no se abren `netflix-ml-interview/stages/**`. Al espacio de la sesión solo se copia `workspace/` o `starter.py`; nunca `flaws.yaml`, `reference.py`, `questions.md` ni `rubric.md`.

### D6 · Base de conocimiento y helper
```
netflix-ml-interview/
  README.md            # español: uso, comandos ::, lang, regla de honor, escala pedagógica, niveles extrapolados
  catalog.yaml  study-map.yaml  sources.md  requirements.txt   # requirements: numpy, pandas (solo contenido)
  stages/<stage>/brief.md  questions.md  rubric.md
  stages/coding/problems/<id>/{problem.md, starter.py, tests.py, reference.py, followups.md}
  stages/technical-screen/prs/<id>/{pr.diff, context.md, issues.md}   datasets/<id>.sql
  stages/ai-assisted-coding/repos/<id>/{workspace/, tasks.md, flaws.yaml, notes.md}
  stages/presentation/takehomes/<id>/{prompt.md, generate_data.py}
  templates/{scorecard.md, debrief.md, session.yaml}
  examples/{transcripts/, gold/}            # transcripciones sintéticas, nunca sesiones reales
  scripts/sim.py  scripts/check_simulator.py  scripts/test_*.py   # stdlib
  sessions/            # IGNORADO por git
.claude/skills/netflix-ml-interview/{SKILL.md, references/relay-protocol.md}
.claude/agents/netflix-*.md (17)
.claude/settings.json  # allow: Bash(python netflix-ml-interview/scripts/sim.py:*), Bash(python3 …:*), Bash(py …:*)
```
- **Subcomandos de `sim.py`**:
  - sesión y entorno: `guard`, `new`, `state`, `info` (entorno y `CLAUDE_CODE_REMOTE`);
  - cada turno: `turn`, `log`, `pause`;
  - preparación: `select` (elige preguntas o problema sin repetir los usados y prepara el *launch packet*);
  - código: `run-tests`, `apply`;
  - evaluación: `verify-scorecard`;
  - recuperación: `rebuild`;
  - historial: `progress`.
- **Intérprete de Python**: al configurar, la skill prueba `python`, `python3` y `py`, y guarda en `session.yaml` el que funciona.
- **Idioma**:
  - La skill, los agentes y la base de conocimiento están en inglés.
  - La configuración se pregunta en inglés, salvo que se pase `lang=es`.
  - El README va en español.
- **Dependencias**:
  - `sim.py` y `check_simulator.py` usan solo stdlib.
  - Los problemas que necesitan numpy o pandas lo declaran en `problem.md`. `check_simulator` los salta con un aviso si faltan; CI instala `requirements.txt`.
  - El SQL se ejecuta sobre `sqlite3`.

### D7 · Evaluación, corte y debrief (reglas pedagógicas)
- **Rúbrica**:
  - Cada competencia tiene un `id` estable, `core: true|false`, `memo_values[]` (solo la de cultura) y una barra "Yes" observable por nivel (L4/L5/L6).
  - Las demás puntuaciones se definen respecto a esa barra: Strong No contradice la barra o tiene errores graves; No no la alcanza; Strong Yes alcanza la barra del nivel superior.
  - Cada rúbrica lleva `rubric_version`.
  - L4 y L6 están extrapolados a partir de L5, y el README lo dice.
- **Recomendación por etapa**. Es una regla del simulador, no de Netflix:
  - **fail**: algún core en Strong No, o dos o más core en No.
  - **insufficient signal**: algún core en "no evidence".
  - **pass**: el resto, siempre que no haya ningún Strong No y como máximo un no-core esté en No.
  - **Nivel observado**: el más alto cuya barra Yes cumplen todos los core.
- **Pistas**: un `nudge` limita la competencia afectada a Yes; un `substantive` que hizo falta para avanzar la limita a No. Nunca afectan a otras competencias.
- **Fin de etapa**: guardado en `end_reason`.
  - Causa externa (`::end`, interrupción): la competencia queda en "no evidence".
  - Causa del candidato (agotó el tiempo, o dejó puntos sin cubrir pese a la redirección): la competencia se puntúa y se listan los puntos que faltaron.
- **Cambio de idioma**: se anota, pero no penaliza.
- **Evaluador**:
  - En feedback inmediato corre en primer plano; en diferido, en segundo plano.
  - Barrera: antes del corte y del debrief tienen que existir todos los scorecards.
  - Recibe la transcripción filtrada (sin `notes_private`), la config y la rúbrica.
  - Cada prueba de evidencia es `{turn_id, quote}` de un turno **del candidato**.
  - `sim.py verify-scorecard` comprueba que cada cita aparece literal en su turno. Si falla, se reanuda al evaluador una vez; si sigue fallando, la competencia pasa a "no evidence" y se avisa.
- **Debrief** (corte y final), en dos pasos:
  1. **Regla determinista** → `provisional_outcome`:
     - **No Hire**: un core en Strong No en una etapa `high`, o veredicto de cultura negativo, o una etapa `high` en fail.
     - **Referred**: todas las `high` de VO1 en pass, cultura positiva y fails solo en `ml-depth`/`hm-onsite` o por encaje débil con el dominio.
     - **Hire**: el resto, con mayoría ponderada en pass.
     - **Nivel**: el mínimo de los niveles observados en las etapas `high`.
  2. **Override**: el HM, como informed captain, puede discrepar, pero solo con una justificación que cite scorecards (`override: true`).
- **Cultura**: se agrega **por valor del memo** a través de las etapas, sin sumar por etapa.
- **Simulación del debrief**:
  - Lee los scorecards en orden de catálogo.
  - Un entrevistador simulado que "cambia de opinión" solo puede citar evidencia que ya esté en un scorecard.
  - Si el HM abre una transcripción, se dice cuál y por qué.
- **Corte**: aplica la misma regla a los scorecards existentes; si no hay screens evaluados, lo dice. Si el corte es negativo, se ofrece seguir en modo `practice`: la decisión real se mantiene y las etapas de práctica solo aportan feedback.
- **Referred**: se ofrece repetir la VO2 con otro dominio (`ml-depth` + `hm-onsite`).
- **Plan de estudio**: las 1–3 recomendaciones son los primeros puntos del plan. `study-map.yaml` asigna a cada id de competencia un módulo de `recsys-course/` o una alternativa (`practice_stage`, `memo`, `resource`).
- **Calidad del juez**: un gold set en `examples/gold/` con transcripciones de casos fuerte, límite y débil, una larga y superficial, una con efecto halo, una con intento de manipulación, y la misma en EN y ES. Cada una se puntúa 3 veces y se registra en `RESULTS.md`.

### D8 · Sesiones solo locales
- `.gitignore` raíz con `netflix-ml-interview/sessions/`.
- `sim.py guard` es la única puerta de escritura. Exige dos condiciones:
  - `git check-ignore -q netflix-ml-interview/sessions/.probe` devuelve 0;
  - `git ls-files netflix-ml-interview/sessions` está vacío.

  Si `git rev-parse` falla (no hay repo), permite escribir con un aviso. El código 128 es un error.
- La skill no contiene `git add`, `commit` ni `push`. `check_simulator` lo verifica, y un test crea una sesión en un repo temporal y comprueba que `git status --porcelain` queda vacío.
- `sim.py info` detecta `CLAUDE_CODE_REMOTE == "true"` para mostrar el aviso de entorno efímero.
- `PROGRESS.md` se regenera desde los `session.yaml` y los front-matter de los scorecards.

### D9 · Reconstrucción y modo degradado
- **Reconstrucción** (`sim.py rebuild`): se usa al reanudar una instancia `in_progress` en otra conversación, o si `SendMessage` falla. Lanza un agente nuevo (`attempt+1`) con:
  - el brief;
  - la transcripción con `<meta>`;
  - el tiempo restante;
  - la orden *"continue as the same persona; do not re-introduce yourself; respond to the last candidate message"*.
- **Modo degradado**: si `SendMessage` no está disponible, la etapa se conduce en el hilo principal con la persona. La evaluación sigue siendo un agente aparte, y se registra `mode: degraded`.
- **Elección de sesión**: `resume` toma la sesión pendiente más reciente; si hay varias, las lista.
- **Coste y compactación**: para el loop completo se recomienda una fase por conversación. Tras una compactación, la skill relee `relay-protocol.md` y `sim.py state`.

### D10 · Formatos congelados
- **catalog.yaml**:
  - `version`
  - `domains[]`
  - `roles{mle|rs|ds}{label, cut, default_domain, loop{screen|vo1|vo2: [stage@variant]}, weights{stage: high|normal|low}}`
  - `stages[]{id, order, default_phase, minutes, persona{name, title, style}, agent, variants[]{id, roles[], minutes?, materials?}, variant_by_role{mle|rs|ds}, competencies[]{id, core}}`
- **rubric.md**:
  - front-matter `{stage, rubric_version}`;
  - al principio, una sección compartida con las definiciones de Strong No, No y Strong Yes;
  - una sección `## <competency_id>` por competencia, con `core: true|false` (más `memo_values:` en la de cultura) y una tabla `| Level | Yes bar |` con L4, L5 y L6.
- **questions.md**: una sección `### <id>` por pregunta, con un bloque YAML `{roles, levels, variant, domain, kind: main|followup|culture, signal_points[]}`, el enunciado y las repreguntas. Mínimo 2 preguntas `main` por cada combinación de rol aplicable y variante.
- **session.yaml**:
  - `{id, created, role, level, lang, domain, time_scale, python, env_ephemeral}`
  - `feedback: immediate|deferred`
  - `mode: normal|practice|degraded`
  - `background_path?`, `candidate_profile?`
  - `instances[]{instance_id, stage, variant, phase, status: pending|in_progress|done|skipped, end_reason?, segments[], agent_name, attempt, question_ids[], problem_id?, scorecard?}`
  - `cut?{outcome, reason}`, `final?{outcome, level, override}`
- **Transcripción**: front-matter con la instancia y la config; después, un bloque por turno `### T<n> · interviewer|candidate|orchestrator|ai-pair · t=MMm` con el texto literal y `<meta>` en YAML.
- **Scorecard**: front-matter `{instance_id, stage, variant, level, rubric_version, recommendation: pass|fail|insufficient_signal, level_observed, scores{<comp_id>: SN|N|Y|SY|no_evidence}, evidence{<comp_id>: [{turn_id, quote}]}, hints[]}`, seguido de prosa en el idioma de la sesión. Los enums van siempre en inglés.
- **flaws.yaml**: `flaws[]{id, zone, trigger_keywords[], description, hidden_test}`. El `hidden_test` falla con el error y pasa sin él.
- **study-map.yaml**: `{<stage>.<competency_id>: {course: [recsys-course/NN_x/], practice_stage?, resource?}}`.
- **Launch packet**: la config, la persona, `brief.md`, las preguntas o el problema seleccionados, `candidate_profile`, el contrato D2 y la regla de idioma.

## Risks / Trade-offs

- [El relevo asíncrono es nuevo y frágil] → Spike obligatorio (tarea 3.0) antes de escribir los 17 agentes, protocolo escrito en `relay-protocol.md` y reconstrucción (D9).
- [Coste: cada turno re-lee la transcripción del agente y la caché caduca a los ~5 min] → Agentes en sonnet salvo los críticos, `<meta>` breve y una fase por conversación.
- [El juez es indulgente o inventa citas] → Verificación literal de citas, reglas deterministas, gold set y "no evidence".
- [Proceso de Netflix inexacto o cambiante, con mucha evidencia que viene de loops de SWE] → Confianza explícita en `sources.md`, corte opcional fuera de MLE, niveles extrapolados declarados y catálogo editable.
- [El candidato puede ver el contenido] → Regla de honor y nada sensible en el espacio de la sesión.
- [Pérdida del historial en contenedores efímeros] → Consecuencia aceptada; se avisa al iniciar.

## Migration Plan

No aplica: es un añadido nuevo. Para deshacerlo basta con borrar `.claude/skills/netflix-ml-interview/`, `.claude/agents/netflix-*.md` y `netflix-ml-interview/`, y quitar la entrada del `.gitignore` y la de `.claude/settings.json`.

## Open Questions

- ¿Añadir más adelante un agente "candidato simulado" que automatice el gold set y los smoke tests? Sería un change aparte.
